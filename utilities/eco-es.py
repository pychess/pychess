# http://es.wikipedia.org/wiki/Anexo:Aperturas_de_ajedrez

import xml.etree.ElementTree as ET


def local2eng(text):
    text = text.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    text = (
        text.replace("R", "K")
        .replace("T", "R")
        .replace("D", "Q")
        .replace("C", "N")
        .replace("A", "B")
    )
    return text


if __name__ == "__main__":
    xhtml = "eco-es.html"
    tree = ET.parse(xhtml)

    # All xml tags are namespace prefixed in parsed tree !
    ns = "{http://www.w3.org/1999/xhtml}"

    ecofile = open("eco.pgn", "w")

    rows = [c for c in tree.findall(".//%sli" % ns) if c.text and c.text[0] in "ABCDE"]

    eco_count = 0
    for row in rows:
        data = []

        if row.text:
            data.append(row.text[:3])
        else:
            continue

        names = []

        if len(row.text) > 4:
            names.append(row.text[4:])

        refs = row.findall("%sa" % ns)
        for ref in refs:
            names.append(ref.text)
            if ref.tail:
                names.append(ref.tail)
        data.append("".join(names))

        print(data)

        if data:
            print('[ECO "%s"]' % data[0], file=ecofile)
            print(
                '[Opening "%s"]' % data[1].replace("\u2026", "...").encode("latin_1"),
                file=ecofile,
            )
            print(file=ecofile)
            print("*", file=ecofile)
            print(file=ecofile)

            eco_count += 1

        # row.text is empty for B50
        if data[0] == "B49":
            print('[ECO "B50"]', file=ecofile)
            print('[Opening "Siciliana"]', file=ecofile)
            print(file=ecofile)
            print("*", file=ecofile)
            print(file=ecofile)

            eco_count += 1

        if data[0] == "E99":
            break

    print("%s lines" % eco_count)

    ecofile.close()
