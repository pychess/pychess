var spinner_html="<img class='spinner' src='http://www.google.com/ig/images/spinner.gif' width='16' height='16' />";
var invalid_str="The requested URL <code>.*</code> was not found on this server.";
var invalid_re=new RegExp(invalid_str);var invalidForm_str="<center><form action='#'><table cellpadding='0' cellspacing='0'><tr><td align='left' style='font-size: 12px'>The specified project does not exist.<br />Please enter a valid project name:</td></tr><tr><td align='center'><input size='30' id='projectName' name='projectName' /></td></tr><tr><td align='right'><input type='submit' id='name_submit' value='Load Project'/></td></tr></table></form></center>";
var url_str="";var PAGE_PREV=-1;var PAGE_NEXT=-2;var PAGE_MORE=-3;function adjustIFrameHeight(){try{gadgets.window.adjustHeight()
}catch(A){}}function fetch(A,E,C,B){var D={};D[gadgets.io.RequestParameters.CONTENT_TYPE]=C;
if(B){D[gadgets.io.RequestParameters.NUM_ENTRIES]=B}gadgets.io.makeRequest(A,E,D)
}function fetchAsString(A,B){fetch(A,B,gadgets.io.ContentType.TEXT)}function fetchAsDom(A,B){fetch(A,B,gadgets.io.ContentType.DOM)
}function fetchAsFeed(A,C,B){fetch(A,C,gadgets.io.ContentType.FEED,B)}function fetchAsStringLegacy(A,B){fetchAsString(A,function(C){B(C.text)
})}function init(){$("#content_div").html("<div id='loading_div'>"+spinner_html+"</div>");
prefs_obj=new gadgets.Prefs();projectName_str=prefs_obj.getString("projectName");
if(projectName_str==""){printProjectForm();return }url_str=url_tmpl.replace("%PROJECT%",projectName_str);
fetchAsString(url_str,function(A){projectLoaded(A.text)})}function projectLoaded(A){if(A.search(invalid_re)==-1){$("#content_div").empty();
render(A)}else{printProjectForm()}}function printProjectForm(){$("#content_div > #loading_div").html(invalidForm_str);
adjustIFrameHeight();$("#name_submit").click(function(){projectName_str=_esc($("#projectName").val());
prefs_obj.set("projectName",projectName_str);gadgets.window.setTitle(title_tmpl.replace("%PROJECT%",projectName_str));
init()})}function generatePagingFromPage(F,E){next_re=new RegExp(/<a href=".+">Next.*<\/a>/);
prev_re=new RegExp(/<a href=".+">.*Prev<\/a>/);var D=jQuery(".pagination:first",jQuery(F)).html();
var C="";var I=false;var H=0;var G=0;var B=0;var A=0;if(D==null){return""}if(D.match(next_re)||D.match(prev_re)){G=new String(D.match(/.*of.*/)).replace(/.*of\ /,"");
B=Math.ceil(G/10);H=Math.min(B,4);A=Math.floor(E/10)+1}I=A==H&&H<B;return H>0?generatePaging(H,A,I,G):""
}function generatePaging(E,B,D,C){var A="";if(E==1){return""}switch(E){case 4:A=B==4?"4&nbsp;"+A:"<a href='#' id='page4'>4</a>&nbsp;"+A;
case 3:A=B==3?"3&nbsp;"+A:"<a href='#' id='page3'>3</a>&nbsp;"+A;case 2:A=B==2?"2&nbsp;"+A:"<a href='#' id='page2'>2</a>&nbsp;"+A;
case 1:A=B==1?"1&nbsp;"+A:"<a href='#' id='page1'>1</a>&nbsp;"+A;break;default:break
}if(B>1){A="<a href='#' id='prev'>Previous</a>&nbsp;"+A}if(B<E){A+="<a href='#' id='next'>Next</a>&nbsp;"
}else{if(B==E&&D){A+="<br /><a href='#' id='more'>See all items</a>"}}return A}function addPagingEvents(A){$("#prev").click(function(B){B.preventDefault();
A(PAGE_PREV)});$("#next").click(function(B){B.preventDefault();A(PAGE_NEXT)});$("#page4").click(function(B){B.preventDefault();
A(4)});$("#page3").click(function(B){B.preventDefault();A(3)});$("#page2").click(function(B){B.preventDefault();
A(2)});$("#page1").click(function(B){B.preventDefault();A(1)});$("#more").click(function(B){B.preventDefault();
A(PAGE_MORE)})}function ellipsify(B,A){if(B.length<=A){return B}return B.substr(0,A).concat("...")
}function ellipsifyWords(C,A){var B;words_arr=C.split(" ");for(B=0;B<words_arr.length;
B++){words_arr[B]=ellipsify(words_arr[B],A)}return words_arr.join(" ")}var url_tmpl="http://code.google.com/p/%PROJECT%/source/list";
var title_tmpl="%PROJECT% changes";var feed_tmpl="http://code.google.com/feeds/p/%PROJECT%/hgchanges/basic?path=%PATH%";
var row_tmpl="<tr><td valign='top' style='border-bottom: 1px solid #BBBBBB;'><a href='%LINK%' target='_blank'>%REVISION%</a></td><td valign='top' style='border-bottom: 1px solid #BBBBBB;'>%TITLE%</td></tr>";
var prefs_obj=new gadgets.Prefs();var projectName_str="";var currentPage_num=1;var feedURL_str="";
var path_str=prefs_obj.getString("path");function render(A){feedURL_str=feed_tmpl.replace("%PROJECT%",_hesc(projectName_str)).replace("%PATH%",_hesc(path_str));
fetchAsFeed(feedURL_str,renderCallback)}function renderCallback(J){var I="";if(J.data){I+="<center><table cellspacing='0' cellpadding='0' width='100%' id='#resultstable'>";
var H="";var B="";var F;var A=Math.ceil(J.data.Entry.length/5);A=Math.min(A,3);var G=J.data.Entry.length>15;
var D=(currentPage_num-1)*5;var C=Math.min(D+5,J.data.Entry.length);for(var E=D;E<C;
E++){H=J.data.Entry[E].Title;F=H.search(":");B="r"+H.substring(9,F);H=H.substring(F+2,H.length);
H=ellipsify(H,100);I+=row_tmpl.replace("%REVISION%",_hesc(B)).replace("%TITLE%",_hesc(H)).replace("%LINK%",_hesc(J.data.Entry[E].Link))
}I+="</table>";I+=generatePaging(A,currentPage_num,G,J.data.Entry.length);I+="</center>"
}else{I+="No changes could be found."}$("#content_div").html(I);addPagingEvents(pagingCallback);
adjustIFrameHeight()}function pagingCallback(A){if(A==PAGE_MORE){window.open(url_tmpl.replace("%PROJECT%",_hesc(projectName_str)),"_blank");
return }if(A==PAGE_PREV){currentPage_num--}else{if(A==PAGE_NEXT){currentPage_num++
}else{currentPage_num=A}}fetchAsJson(feedURL_str,renderCallback,16,true)}gadgets.util.registerOnLoadHandler(init);
