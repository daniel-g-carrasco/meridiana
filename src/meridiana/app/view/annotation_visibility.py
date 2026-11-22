"""Exact visible intervals of annotations, computed on real scene triangles in a job.

Each triangle casts a convex shadow volume. Intersecting a segment with its four
half spaces gives an interval, without sampling rays or filling a mesh's empty box.
The complement of the merged intervals is the visible part of the segment.
"""
from __future__ import annotations

import math
import numpy as np

from meridiana.app import layout_job, scene_job
from meridiana.app.work.job import Kind

KIND = Kind(name='annotation_visibility', title=scene_job.KIND.title,
            run='meridiana.app.view.annotation_visibility:run', home=layout_job.KIND.name,
            keep_warm=layout_job.SESSION, settle=0.0, in_bar=False)
CHUNK = 32768
FACE_TOLERANCE = .001


def visible_intervals(triangles, a, b, camera, checkpoint=lambda: None):
    """Visible parameters along a-b, in Qt scene axes; includes both sides of faces."""
    a, b, origin = (np.asarray(v, float) for v in (a, b, camera['origin']))
    direction = b-a
    triangles = np.asarray(triangles).reshape(-1, 3, 3)
    hidden = []
    for first in range(0, len(triangles), CHUNK):
        checkpoint()
        t = np.asarray(triangles[first:first+CHUNK], float)
        low, high = np.zeros(len(t)), np.ones(len(t))
        valid = np.ones(len(t), bool)

        def clip(normal, anchor, sign, margin=0.):
            nonlocal low, high, valid
            size = np.linalg.norm(normal, axis=1)
            normal = np.divide(normal, size[:, None], out=np.zeros_like(normal), where=size[:, None] > 1e-12)
            value = np.einsum('ij,ij->i', a-anchor, normal)*sign-margin
            slope = normal@direction*sign
            cross = np.divide(-value, slope, out=np.zeros_like(value), where=np.abs(slope) > 1e-12)
            low = np.where(slope > 1e-12, np.maximum(low, cross), low)
            high = np.where(slope < -1e-12, np.minimum(high, cross), high)
            valid &= (size > 1e-12) & ((np.abs(slope) > 1e-12) | (value >= 0)) & (low <= high)

        for i in range(3):
            j, k = (i+1) % 3, (i+2) % 3
            if camera['ortho']:
                normal = np.cross(t[:, j]-t[:, i], camera['forward'])
                anchor = t[:, i]
            else:
                normal = np.cross(t[:, i]-origin, t[:, j]-origin)
                anchor = np.broadcast_to(origin, (len(t), 3))
            sign = np.where(np.einsum('ij,ij->i', t[:, k]-anchor, normal) >= 0, 1., -1.)
            clip(normal, anchor, sign)
        normal = np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0])
        toward_camera = -np.asarray(camera['forward']) if camera['ortho'] else origin-t[:, 0]
        side = np.sum(normal*toward_camera, axis=1)
        # Strictly behind the face; a measurement on the face remains visible.
        clip(normal, t[:, 0], np.where(side >= 0, -1., 1.), FACE_TOLERANCE)
        valid &= np.abs(side) > 1e-12
        hidden.extend(zip(low[valid].tolist(), high[valid].tolist(), strict=True))
    out, end = [], 0.
    for low, high in sorted(hidden):
        if low > end+1e-9:
            out.append((end, low))
        end = max(end, high)
    if end < 1.-1e-9:
        out.append((end, 1.))
    return out


def qt(points):
    p = np.asarray(points, float)
    return p[..., [0, 2, 1]]*np.array([1., 1., -1.])


def ray_hit(triangles, origin, direction, checkpoint=lambda: None):
    """Closest actual face under a moving pointer, without a GUI-thread probe."""
    origin, direction = np.asarray(origin, float), np.asarray(direction, float)
    nearest = float('inf')
    for first in range(0, len(triangles), CHUNK):
        checkpoint()
        tri = np.asarray(triangles[first:first+CHUNK], float)
        u, v = tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
        p = np.cross(direction, v)
        det = np.einsum('ij,ij->i', u, p)
        inv = np.divide(1., det, out=np.zeros_like(det), where=np.abs(det) > 1e-12)
        s = origin-tri[:, 0]
        b1 = np.einsum('ij,ij->i', s, p)*inv
        q = np.cross(s, u)
        b2 = (q@direction)*inv
        distance = np.einsum('ij,ij->i', v, q)*inv
        hit = (np.abs(det) > 1e-12) & (b1 >= -1e-9) & (b2 >= -1e-9) & (b1+b2 <= 1+1e-9) & (distance > 0)
        if hit.any():
            nearest = min(nearest, float(distance[hit].min()))
    return origin+nearest*direction if math.isfinite(nearest) else None


def clip_segment(a, b, camera):
    if 'right' not in camera:             # pure callers may ask only for solid visibility
        return a, b
    def planes(p):
        v = p-np.asarray(camera['origin'])
        z = np.dot(v, camera['forward'])
        x, y = np.dot(v, camera['right']), np.dot(v, camera['up'])
        h = camera['halfHeight'] if camera['ortho'] else z*camera['tangent']
        return np.array([z-.01, camera['far']-z, h*camera['aspect']-x, h*camera['aspect']+x, h-y, h+y])
    pa, pb = planes(a), planes(b)
    lo, hi = 0., 1.
    for va, vb in zip(pa, pb, strict=True):
        if va < 0 and vb < 0:
            return None
        if va < 0:
            lo = max(lo, va/(va-vb))
        if vb < 0:
            hi = min(hi, va/(va-vb))
    return (a+(b-a)*lo, a+(b-a)*hi) if lo <= hi else None


def calculate(triangles, request, checkpoint=lambda: None):
    camera = request['camera']
    segments, points = {}, {}
    for segment in request['segments']:
        a, b = qt(segment['a']), qt(segment['b'])
        if 'ray' in segment:
            origin, direction = segment['ray']
            at = ray_hit(triangles, origin, direction, checkpoint)
            if at is None and camera.get('ground', False) and abs(direction[1]) > 1e-12:
                t = -origin[1]/direction[1]
                if t > 0:
                    at = np.asarray(origin)+t*np.asarray(direction)
            if at is None:
                segments[segment['key']] = []
                continue
            if segment.get('rayAt') == 'a':
                a = at
            else:
                b = at
        clipped = clip_segment(a, b, camera)
        if clipped is None:
            segments[segment['key']] = []
            continue
        a, b = clipped
        intervals = visible_intervals(triangles, a, b, camera, checkpoint)
        a, b = a[[0, 2, 1]]*np.array([1, -1, 1]), b[[0, 2, 1]]*np.array([1, -1, 1])
        segments[segment['key']] = [dict(a=(a+(b-a)*lo).tolist(), b=(a+(b-a)*hi).tolist()) for lo, hi in intervals]
    for point in request['points']:
        p = qt(point['at'])
        points[point['key']] = bool(np.dot(p-np.asarray(camera['origin']), camera['forward']) > 0
                                    and visible_intervals(triangles, p, p, camera, checkpoint))
    return dict(segments=segments, points=points)


def _geometry(request, ctx):
    answer = scene_job.run(request, ctx)
    if answer.get('missing'):
        raise ValueError('The scene layouts are not ready for annotation visibility')
    triangles = answer['triangles'][0].reshape(-1, 3, 3)
    context = request.get('context')
    if context:
        from meridiana.app.exchange import ifc_mesh
        hidden = set(map(tuple, context['hidden']))
        keep, first = np.ones(len(triangles), bool), 0
        for part, oid, count in answer['owners']:
            if (part, oid) in hidden:
                keep[first:first+count] = False
            first += count
        triangles = triangles[keep]
        mesh = ifc_mesh.load(context['path'])
        pieces = [triangles]
        angle = math.radians(context['turn'])
        c, s = math.cos(angle), math.sin(angle)
        for i in range(len(mesh['pieces'])):
            ctx.checkpoint()
            vertices, faces, colour = ifc_mesh.piece(mesh, i, context['skip'])
            if colour[3] <= 0:
                continue
            p = qt(vertices)
            p = np.column_stack((p[:, 0]*c+p[:, 2]*s, p[:, 1], -p[:, 0]*s+p[:, 2]*c))
            p += context['position']
            pieces.append(p[faces])
        triangles = np.concatenate(pieces)
    # The modules are actual cube instances, including their thin sides.
    table = answer['table']
    if len(table):
        corners = np.array([[x, y, z] for x in (-50., 50.) for y in (-50., 50.) for z in (-50., 50.)])
        faces = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                          [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
        transforms = np.asarray(table[:, :12], float).reshape(-1, 3, 4)
        vertices = np.einsum('vj,nij->nvi', corners, transforms[:, :, :3])+transforms[:, None, :, 3]
        triangles = np.concatenate((triangles, vertices[:, faces].reshape(-1, 3, 3)))
    return triangles


def run(request, ctx):
    kept = ctx.kept.get('annotation_geometry')
    if kept is None or kept[0] != request['scene_key']:
        if 'photo' not in request:
            return dict(missing_scene=True)
        ctx.kept.pop('annotation_geometry', None)
        kept = None
        kept = (request['scene_key'], _geometry(request, ctx))
        ctx.kept['annotation_geometry'] = kept
    return calculate(kept[1], request, ctx.checkpoint)
