void MAIN()
{
    vec2 distanceToEdge = min(UV0, vec2(1.0) - UV0) / max(fwidth(UV0), vec2(0.000001));
    float inside = smoothstep(0.0, 0.8, min(distanceToEdge.x, distanceToEdge.y));
    FRAGCOLOR = mix(vec4(198.0/255.0, 203.0/255.0, 214.0/255.0, 1.0),
                    vec4(25.0/255.0, 45.0/255.0, 90.0/255.0, 1.0), inside);
}
