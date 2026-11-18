// Flat faces from the screen derivatives of the position: no normals in the vertices, a vertex shared by its faces.
// A light from above and two from the sides, fixed, so that the faces of a box read apart as in a CAD viewer.
VARYING vec3 worldPos;
VARYING vec3 toCamera;
void MAIN()
{
    vec3 n = normalize(cross(dFdx(worldPos), dFdy(worldPos)));
    if (dot(n, toCamera) < 0.0) n = -n;
    float light = 0.48 + 0.30 * max(n.y, 0.0) + 0.24 * abs(dot(n, normalize(vec3(0.45, 0.35, 0.82))))
                  + 0.12 * abs(dot(n, normalize(vec3(-0.80, 0.20, -0.30))));
    // a color property reaches the shader in linear light: back to sRGB, as the file's colours are meant
    FRAGCOLOR = vec4(pow(tint.rgb * min(light, 1.0), vec3(1.0 / 2.2)), opacity);
}
