// The corners of a roof (R401): discs of fixed pixel size, drawn in the scene so that a solid covers them as it covers
// the lines. VERTEX is the corner, NORMAL.xy the offset on screen in pixels, NORMAL.z how far towards the camera, in
// pixels too: a corner must not be bitten by the faces it belongs to.
VARYING vec4 dotColor;
void MAIN()
{
    vec3 towards = normalize(CAMERA_POSITION - VERTEX);
    vec4 clip = MODELVIEWPROJECTION_MATRIX * vec4(VERTEX + towards * NORMAL.z * pixelSize, 1.0);
    clip.xy += NORMAL.xy * 2.0 / viewPixels * clip.w;
    POSITION = clip;
    dotColor = COLOR;
}
