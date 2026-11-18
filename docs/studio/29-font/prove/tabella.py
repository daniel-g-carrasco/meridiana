import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
F = d["fonts"]; b = F["inter"]
print("corpus", d["corpus_n"], "non-ascii used:", "".join(d["non_ascii_chars"]))
print(f'{"id":15} {"fasi":>5} {"barra":>5} {"etich":>5} {"verif":>5} {"num":>5} {"fasi6":>5} {"corp":>5} {"corpNH":>6} {"x/em":>5} {"xQt":>4} {"cap":>5} {"h":>3} tab tn 1/0 miss_special | miss_used')
for k, f in F.items():
    g = lambda n: 100 * f["groups"][n] / b["groups"][n]
    print(f'{k:15} {g("fasi"):5.0f} {g("barra"):5.0f} {g("etichette"):5.0f} {g("verifiche"):5.0f} {g("numeri"):5.0f} '
          f'{100*f["groups600"]["fasi"]/b["groups600"]["fasi"]:5.0f} {100*f["corpus"]/b["corpus"]:5.1f} {100*f["corpus_nohint"]/b["corpus_nohint"]:6.1f} '
          f'{f["xheight_em"]:5.3f} {f["xheight_qt"]:4.1f} {f["capheight_em"]:5.3f} {f["height"]:3.0f} {"Y" if f["digits_tabular"] else "n"}   {"Y" if f["gsub_tnum"] else "n"}  {f["digits_1_vs_0"]:.2f} {"".join(f["missing_special"])} | {"".join(f["missing_used"])} {f["size_kb"]} {list(f["axes"])}')
