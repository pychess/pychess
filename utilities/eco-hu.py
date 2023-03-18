# http://hu.wikipedia.org/wiki/Sakkmegnyit%C3%A1sok_list%C3%A1ja

import xml.etree.ElementTree as ET


def local2eng(text):
    text = text.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    text = text.replace("B", "R").replace("V", "Q").replace("H", "N").replace("F", "B")
    return text


if __name__ == "__main__":
    xhtml = "eco-hu.html"
    tree = ET.parse(xhtml)

    # All xml tags are namespace prefixed in parsed tree !
    ns = "{http://www.w3.org/1999/xhtml}"

    ecofile = open("eco.pgn", "w")

    rows = [c for c in tree.findall(".//%sli" % ns) if c.get("class") is None]

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
                '[Opening "%s"]'
                % data[1].replace("\u2026", "...").replace("ő", "ö").encode("latin_1"),
                file=ecofile,
            )
            print(file=ecofile)
            print("*", file=ecofile)
            print(file=ecofile)

            eco_count += 1

        if data[0] == "E99":
            break

    print("%s lines" % eco_count)

    ecofile.close()
