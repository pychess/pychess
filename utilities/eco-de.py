# http://de.wikipedia.org/wiki/ECO-Code

import xml.etree.ElementTree as ET


def local2eng(text):
    text = text.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    text = text.replace("S", "N").replace("L", "B").replace("T", "R").replace("D", "Q")
    return text


if __name__ == "__main__":
    xhtml = "eco-de.html"
    tree = ET.parse(xhtml)

    # All xml tags are namespace prefixed in parsed tree !
    ns = "{http://www.w3.org/1999/xhtml}"

    ecofile = open("eco.pgn", "w")

    tables = [
        c for c in tree.findall(".//%stable" % ns) if c.get("class") == "prettytable"
    ]

    eco_count = 0
    for table in tables:
        rows = [c for c in table.findall("%str" % ns)]

        for row in rows:
            cols = row.findall("%std" % ns)
            data = []
            for i, col in enumerate(cols):
                if i == 0:
                    data.append(col.text)

                elif i == 1:
                    moves = []
                    if col.text:
                        comment1 = col.text.find(" (")
                        comment2 = col.text.find(" ohne")
                        if comment1 != -1:
                            moves.append(col.text[:comment1])
                        elif comment2 != -1:
                            moves.append(col.text[:comment2])
                        else:
                            moves.append(col.text)
                    par = col.findall("%sp" % ns)
                    for p in par:
                        moves.append(p.text)
                    data.append("".join(moves))

                else:
                    names = []
                    if col.text:
                        names.append(col.text)
                    refs = col.findall("%sa" % ns)
                    for ref in refs:
                        names.append(ref.text)
                        if ref.tail:
                            names.append(ref.tail.rstrip())
                    par = col.findall("%sp" % ns)
                    for p in par:
                        if p.text:
                            names.append(p.text)
                    data.append("".join(names))

            # fix some incorrect lines
            if data and data[0] == "A65":
                data[1] = "1. d4 Nf6 2. c4 c5 3. d5 e6 4. Nc3 exd5 5. cxd5 d6 6. e4"
            elif data and data[0] == "C50":
                data[1] = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5"
            elif data and data[0] == "C65":
                data[1] = "1. e4 e5 2. Nf3 Nc6 3. Bb5 Nf6"
            elif data and data[0] == "D00":
                data[1] = "1. d4 d5"
            elif data and data[0] == "D55":
                data[1] = "1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3"
            elif data and data[0] == "E05":
                data[1] = "1. d4 Nf6 2. c4 e6 3. g3 d5 4. Bg2 dxc4 5. Nf3 Be7"
            elif data and data[0] == "E06":
                data[1] = "1. d4 Nf6 2. c4 e6 3. g3 d5 4. Bg2 Be7 5. Nf3"
            elif data and data[0] == "E07":
                data[1] = (
                    "1. d4 Nf6 2. c4 e6 3. g3 d5 4. Bg2 Be7 5. Nf3 O-O 6. O-O Nbd7"
                )
            elif data and data[0] == "E08":
                data[1] = (
                    "1. d4 Nf6 2. c4 e6 3. g3 d5 4. Bg2 Be7 5. Nf3 O-O 6. O-O Nbd7 7. Qc2"
                )
            elif data and data[0] == "E09":
                data[1] = (
                    "1. d4 Nf6 2. c4 e6 3. g3 d5 4. Bg2 Be7 5. Nf3 O-O 6. O-O Nbd7 7. Qc2 c6 8. Nbd2"
                )
            elif data and data[0] == "E32":
                data[1] = "1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. Qc2"

            print(data)

            if data:
                print('[ECO "%s"]' % data[0], file=ecofile)
                print(
                    '[Opening "%s"]'
                    % data[2].replace("\u2026", "...").encode("latin_1"),
                    file=ecofile,
                )
                print(file=ecofile)
                print("%s" % local2eng(data[1]), file=ecofile)
                print(file=ecofile)

                eco_count += 1

    print("%s lines" % eco_count)

    ecofile.close()
