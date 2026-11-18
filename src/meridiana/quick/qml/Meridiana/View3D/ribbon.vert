// Same square tubes as mesh.ribbons, with a camera-dependent metric width.
void MAIN()
{
    vec3 p = VERTEX + NORMAL * ribbonWidth * pixelSize;
    POSITION = MODELVIEWPROJECTION_MATRIX * vec4(p, 1.0);
}
