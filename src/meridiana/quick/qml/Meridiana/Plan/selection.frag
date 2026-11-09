#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 pixelStep;
    vec4 ink;
    vec4 halo;
    float fillOpacity;
};
layout(binding = 1) uniform sampler2D source;
float mask(vec2 offset) { return texture(source, qt_TexCoord0 + offset * pixelStep).a; }
void main() {
    float centre = mask(vec2(0.0));
    float nearMax = centre, nearMin = centre, farMax = centre;
    const vec2 directions[8] = vec2[8](vec2(1,0),vec2(-1,0),vec2(0,1),vec2(0,-1),
        vec2(.707,.707),vec2(-.707,.707),vec2(.707,-.707),vec2(-.707,-.707));
    for (int i=0;i<8;i++) {
        float m = mask(directions[i] * 1.1);
        nearMax = max(nearMax,m); nearMin = min(nearMin,m);
        farMax = max(farMax,mask(directions[i] * 2.1));
    }
    float edge = clamp(nearMax-nearMin,0.0,1.0);
    float light = max(edge,centre*fillOpacity);
    float dark = max(0.0,farMax-centre)*(1.0-light)*halo.a;
    float alpha = light + dark;
    fragColor = vec4(ink.rgb*light + halo.rgb*dark,alpha)*qt_Opacity;
}
