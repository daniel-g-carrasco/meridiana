// Prova per lo studio 16, tema A: lo scheletro dritto di CGAL (Straight_skeleton_2, licenza GPL-3+) come
// riferimento esatto per le implementazioni in Python. Legge dal standard input una pianta (n, poi n righe
// "x y", in senso antiorario) e stampa le facce del tetto: per ogni faccia i suoi vertici con la loro altezza
// (la distanza dalla gronda, "time" dello scheletro).
//
// Compilazione (Ubuntu: apt-get install libcgal-dev libgmp-dev libmpfr-dev libboost-dev):
//     g++ -O2 -std=c++17 -o /tmp/scheletro_cgal docs/studio/16-prove/scheletro_cgal.cpp -lgmp -lmpfr
// Uso dal Python della prova: scheletro.py --backend cgal --cgal /tmp/scheletro_cgal
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Polygon_2.h>
#include <CGAL/create_straight_skeleton_2.h>
#include <cstdio>
#include <iostream>

typedef CGAL::Exact_predicates_inexact_constructions_kernel K;
typedef K::Point_2 Point;
typedef CGAL::Polygon_2<K> Polygon;
typedef CGAL::Straight_skeleton_2<K> Ss;

int main() {
    int n;
    if (!(std::cin >> n)) return 1;
    Polygon poly;
    for (int i = 0; i < n; ++i) {
        double x, y;
        std::cin >> x >> y;
        poly.push_back(Point(x, y));
    }
    if (!poly.is_counterclockwise_oriented()) poly.reverse_orientation();
    auto ss = CGAL::create_interior_straight_skeleton_2(poly.vertices_begin(), poly.vertices_end());
    if (!ss) { std::printf("ERROR\n"); return 2; }
    for (auto f = ss->faces_begin(); f != ss->faces_end(); ++f) {
        auto h = f->halfedge();
        auto start = h;
        std::printf("face");
        do {
            auto v = h->vertex();
            std::printf(" %.9g %.9g %.9g", v->point().x(), v->point().y(), v->time());
            h = h->next();
        } while (h != start);
        std::printf("\n");
    }
    return 0;
}
