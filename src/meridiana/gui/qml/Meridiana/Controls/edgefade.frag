#version 440
// EdgeFades.qml: what scrolls dissolves into whatever lies under it near the edges with more content beyond them
// (R624). `topBand` and `bottomBand` are the heights of the two dissolves in logical pixels (0: none), `room` the bar's lane
// at the right, left whole. Smoothstep: no kink where the dissolve starts or ends, so no visible band.
// R633: `topInset` and `bottomInset`, the heads held at the edges (HeldHeads.qml): nothing of the content under them, the
// dissolve starts at their edge.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 area;
    float topBand;
    float bottomBand;
    float room;
    float topInset;
    float bottomInset;
};
layout(binding = 1) uniform sampler2D source;
void main() {
    float y = qt_TexCoord0.y * area.y;
    float top = y - topInset;
    float bottom = area.y - bottomInset - y;
    float k = top < 0.0 || bottom < 0.0 ? 0.0 : 1.0;
    if (topBand > 0.0) k *= smoothstep(0.0, topBand, top);
    if (bottomBand > 0.0) k *= smoothstep(0.0, bottomBand, bottom);
    if (qt_TexCoord0.x * area.x >= area.x - room) k = 1.0;
    fragColor = texture(source, qt_TexCoord0) * (k * qt_Opacity);
}
