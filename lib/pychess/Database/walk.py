def walk(node, arr, txt):
    while True: 
        if node is None:
            break
        
        # Initial game or variation comment
        if node.prev is None:
            for child in node.children:
                if isinstance(child, basestring):
                    arr.append(COMMENT)
                    txt.append(child)
            node = node.next
            continue

        arr.append(node.board.history[-1][0])

        for nag in node.nags:
            if nag:
                arr.append(NAG + int(nag[1:]))

        for child in node.children:
            if isinstance(child, basestring):
                # comment
                arr.append(COMMENT)
                txt.append(child)
            else:
                # variations
                arr.append(VARI_START)
                walk(child[0], arr, txt)
                arr.append(VARI_END)

        if node.next:
            node = node.next
        else:
            break
