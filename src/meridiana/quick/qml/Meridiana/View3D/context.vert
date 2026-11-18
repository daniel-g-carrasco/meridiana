// The true geometry of an imported IFC (r21-ifc-vista): positions only, the normal is made in context.frag.
VARYING vec3 worldPos;
VARYING vec3 toCamera;
void MAIN()
{
    worldPos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    toCamera = CAMERA_POSITION - worldPos;
    POSITION = MODELVIEWPROJECTION_MATRIX * vec4(VERTEX, 1.0);
}
