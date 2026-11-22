// The true geometry of an imported IFC (r21-ifc-vista). Flat faces from the screen derivatives of the position (no
// normals in the vertices, a vertex shared by its faces), lit as in a CAD viewer by a light from above and two from
// the sides, fixed, so that the faces of a box read apart. R603 (second part): the sun's shadow (the model's own, the other
// buildings', the plant's) and the faces turned away from the sun take that light down to shadeLevel; a face in the
// sun is at shadeLevel + sunLevel (Viewport.qml, the tokens d3 light_*). Qt's lights only say where the sun's shadow
// falls: their own diffuse and specular light is not used, so the look stays the file's colours.
VARYING vec3 worldPos;
VARYING vec3 toCamera;
void MAIN()
{
    vec3 n = normalize(cross(dFdx(worldPos), dFdy(worldPos)));
    if (dot(n, toCamera) < 0.0) n = -n;
    NORMAL = n;
    float light = 0.48 + 0.30 * max(n.y, 0.0) + 0.24 * abs(dot(n, normalize(vec3(0.45, 0.35, 0.82))))
                  + 0.12 * abs(dot(n, normalize(vec3(-0.80, 0.20, -0.30))));
    // a color property reaches the shader in linear light, and the scene's tonemapping takes the sum back to sRGB
    BASE_COLOR = vec4(1.0, 1.0, 1.0, opacity);
    EMISSIVE_COLOR = tint.rgb * min(light, 1.0);
    METALNESS = 0.0;
    ROUGHNESS = 1.0;
}
void AMBIENT_LIGHT()
{
}
void SPECULAR_LIGHT()
{
}
void DIRECTIONAL_LIGHT()
{
    // the sun is the light towards toSun: how much of it reaches this face (0 in the shadow or turned away, 1 in the
    // sun) goes to POST_PROCESS in DIFFUSE's red, that it was met in DIFFUSE's green. A face edge-on to the sun fades
    // instead of flickering (the shadow map's acne)
    if (dot(TO_LIGHT_DIR, toSun) > 0.999) {
        float facing = smoothstep(0.0, 0.08, dot(NORMAL, TO_LIGHT_DIR));
        float lit = clamp((SHADOW_CONTRIB - shadowFloor) / max(1.0 - shadowFloor, 0.01), 0.0, 1.0);
        DIFFUSE = vec3(facing * lit, 1.0, 0.0);
    }
}
void POST_PROCESS()
{
    float level = sunShadows && DIFFUSE.g > 0.5 ? shadeLevel + sunLevel * DIFFUSE.r : 1.0;
    COLOR_SUM = vec4(EMISSIVE * level, COLOR_SUM.a);
}
