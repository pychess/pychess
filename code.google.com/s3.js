var spinner_html = "<img class='spinner' src='http://www.google.com/ig/images/spinner.gif' width='16' height='16' />";
var invalid_str = "The requested URL <code>.*</code> was not found on this server.";
var invalid_re = new RegExp(invalid_str);
var invalidForm_str = "<center><form action='#'><table cellpadding='0' cellspacing='0'><tr><td align='left' style='font-size: 12px'>The specified project does not exist.<br />Please enter a valid project name:</td></tr><tr><td align='center'><input size='30' id='projectName' name='projectName' /></td></tr><tr><td align='right'><input type='submit' id='name_submit' value='Load Project'/></td></tr></table></form></center>";
var url_str = "";
var PAGE_PREV = -1;
var PAGE_NEXT = -2;
var PAGE_MORE = -3;
function adjustIFrameHeight() {
    try {
        gadgets.window.adjustHeight()
    } catch (A) {
    }
}
function fetch(A, E, C, B) {
    var D = {};
    D[gadgets.io.RequestParameters.CONTENT_TYPE] = C;
    if (B) {
        D[gadgets.io.RequestParameters.NUM_ENTRIES] = B
    }
    gadgets.io.makeRequest(A, E, D)
}
function fetchAsString(A, B) {
    fetch(A, B, gadgets.io.ContentType.TEXT)
}
function fetchAsDom(A, B) {
    fetch(A, B, gadgets.io.ContentType.DOM)
}
function fetchAsFeed(A, C, B) {
    fetch(A, C, gadgets.io.ContentType.FEED, B)
}
function fetchAsStringLegacy(A, B) {
    fetchAsString(A, function(C) {
        B(C.text)
    })
}
function init() {
    $("#content_div").html("<div id='loading_div'>" + spinner_html + "</div>");
    prefs_obj = new gadgets.Prefs();
    projectName_str = prefs_obj.getString("projectName");
    if (projectName_str == "") {
        printProjectForm();
        return
    }
    url_str = url_tmpl.replace("%PROJECT%", projectName_str);
    fetchAsString(url_str, function(A) {
        projectLoaded(A.text)
    })
}
function projectLoaded(A) {
    if (A.search(invalid_re) == -1) {
        $("#content_div").empty();
        render(A)
    } else {
        printProjectForm()
    }
}
function printProjectForm() {
    $("#content_div > #loading_div").html(invalidForm_str);
    adjustIFrameHeight();
    $("#name_submit").click(function() {
        projectName_str = _esc($("#projectName").val());
        prefs_obj.set("projectName", projectName_str);
        gadgets.window.setTitle(title_tmpl.replace("%PROJECT%", projectName_str));
        init()
    })
}
function generatePagingFromPage(F, E) {
    next_re = new RegExp(/<a href=".+">Next.*<\/a>/);
    prev_re = new RegExp(/<a href=".+">.*Prev<\/a>/);
    var D = jQuery(".pagination:first", jQuery(F)).html();
    var C = "";
    var I = false;
    var H = 0;
    var G = 0;
    var B = 0;
    var A = 0;
    if (D == null) {
        return ""
    }
    if (D.match(next_re) || D.match(prev_re)) {
        G = new String(D.match(/.*of.*/)).replace(/.*of\ /, "");
        B = Math.ceil(G / 10);
        H = Math.min(B, 4);
        A = Math.floor(E / 10) + 1
    }
    I = A == H && H < B;
    return H > 0 ? generatePaging(H, A, I, G) : ""
}
function generatePaging(E, B, D, C) {
    var A = "";
    if (E == 1) {
        return ""
    }
    switch (E) {
        case 4:
            A = B == 4 ? "4&nbsp;" + A : "<a href='#' id='page4'>4</a>&nbsp;" + A;
        case 3:
            A = B == 3 ? "3&nbsp;" + A : "<a href='#' id='page3'>3</a>&nbsp;" + A;
        case 2:
            A = B == 2 ? "2&nbsp;" + A : "<a href='#' id='page2'>2</a>&nbsp;" + A;
        case 1:
            A = B == 1 ? "1&nbsp;" + A : "<a href='#' id='page1'>1</a>&nbsp;" + A;
            break;
        default:
            break
    }
    if (B > 1) {
        A = "<a href='#' id='prev'>Previous</a>&nbsp;" + A
    }
    if (B < E) {
        A += "<a href='#' id='next'>Next</a>&nbsp;"
    } else {
        if (B == E && D) {
            A += "<br /><a href='#' id='more'>See all items</a>"
        }
    }
    return A
}
function addPagingEvents(A) {
    $("#prev").click(function(B) {
        B.preventDefault();
        A(PAGE_PREV)
    });
    $("#next").click(function(B) {
        B.preventDefault();
        A(PAGE_NEXT)
    });
    $("#page4").click(function(B) {
        B.preventDefault();
        A(4)
    });
    $("#page3").click(function(B) {
        B.preventDefault();
        A(3)
    });
    $("#page2").click(function(B) {
        B.preventDefault();
        A(2)
    });
    $("#page1").click(function(B) {
        B.preventDefault();
        A(1)
    });
    $("#more").click(function(B) {
        B.preventDefault();
        A(PAGE_MORE)
    })
}
function ellipsify(B, A) {
    if (B.length <= A) {
        return B
    }
    return B.substr(0, A).concat("...")
}
function ellipsifyWords(C, A) {
    var B;
    words_arr = C.split(" ");
    for (B = 0; B < words_arr.length; 
    B++) {
        words_arr[B] = ellipsify(words_arr[B], A)
    }
    return words_arr.join(" ")
}
var url_tmpl = "http://code.google.com/p/%PROJECT%/";
var title_tmpl = "%PROJECT% issue updates";
var feed_tmpl = "http://code.google.com/feeds/p/%PROJECT%/issueupdates/basic/";
var prefs_obj = new gadgets.Prefs();
var projectName_str = "";
var row_tmpl = "<a id='expansion%NUM%' data-num='%NUM%' class='expansionIcon' title='Show this story' href='javascript:void(0)'/><a style=\"display:block; padding-left: 16px;\" title=\"%SUMMARY%\" href=\"%LINK%\" target='_blank'>%TITLE%</a><div id='expansionContent%NUM%' class='expansionContent'>%SUMMARY%</div>";
var sep_str = "<div style='height: 10px'></div>";
var MINIMIZED_SUMMARY = 0;
var MAXIMIZED_SUMMARY = 1;
var UNHOVERED_EXPANDER_ARR = ["0 -24px", "-12px -24px"];
var HOVERED_EXPANDER_ARR = ["0 -36px", "-12px -36px"];
var stories_arr = [MINIMIZED_SUMMARY, MINIMIZED_SUMMARY, MINIMIZED_SUMMARY];
function render(A) {
    var B = feed_tmpl.replace("%PROJECT%", projectName_str);
    fetchAsDom(B, renderCallback)
}
function renderCallback(D) {
    var I = "";
    if (!D.data) {
        I += "No issue updates could be found."
    }
    var F = D.data.getElementsByTagName("entry");
    for (var E = 0; E < F.length; E++) {
        var K = F[E];
        var A = K.childNodes;
        var J, G, H;
        for (var C = 0; C < A.length; C++) {
            var B = A[C];
            if (B.nodeName == "title") {
                J = B.firstChild.nodeValue
            } else {
                if (B.nodeName == "content") {
                    G = B.firstChild.nodeValue
                } else {
                    if (B.nodeName == "id") {
                        H = B.firstChild.nodeValue;
                        // H is of the form http://code.google.com/feeds/p/PROJECTNAME/issueupdates/basic/NNNN/NN .
                        // Covert it to the form http://code.google.com/p/PROJECTNAME/issues/detail?id=NNNN#cNN .
                        var match = H.match(/feeds\/p\/(.*)\/issueupdates\/basic\/(.*)\/(.*)/);
                        if (match)
                          H = "http://code.google.com/p/" + match[1] + "/issues/detail?id=" + match[2] + "#c" + match[3];
                    }
                }
            }
        }
        I += row_tmpl.replace(/%NUM%/g, String(E)).replace(/%LINK%/g, H).replace(/%TITLE%/g, J).replace(/%SUMMARY%/g, G) + sep_str
    }
    $("#issueupdates_div").html(I);
    addExpansionEvents();
    adjustIFrameHeight()
}
function addExpansionEvents() {
    $(".expansionIcon").click(function(A) {
        var num = A.target.dataset.num;
        A.preventDefault();
        expander(num);
        jQuery(this).css("background-position", HOVERED_EXPANDER_ARR[stories_arr[num]])
    });
    $(".expansionIcon").hover(function(A) {
        var num = A.target.dataset.num;
        A.preventDefault();
        jQuery(this).css("background-position", HOVERED_EXPANDER_ARR[stories_arr[0]])
    }, function(A) {
        A.preventDefault();
        jQuery(this).css("background-position", UNHOVERED_EXPANDER_ARR[stories_arr[0]])
    });
}
function expander(A) {
    if (stories_arr[A] !== MAXIMIZED_SUMMARY) {
        stories_arr[A] = MAXIMIZED_SUMMARY;
        $("#expansionContent" + A).show();
        adjustIFrameHeight()
    } else {
        stories_arr[A] = MINIMIZED_SUMMARY;
        $("#expansionContent" + A).hide();
        adjustIFrameHeight()
    }
}
gadgets.util.registerOnLoadHandler(init);