var invalid_str="The requested URL <code>.*</code> was not found on this server.";
var invalid_re=new RegExp(invalid_str);var invalidForm_str="<center><form action='#'><table cellpadding='0' cellspacing='0'><tr><td align='left' style='font-size: 12px'>The specified project does not exist.<br />Please enter a valid project name:</td></tr><tr><td align='center'><input size='30' id='projectName' name='projectName' /></td></tr><tr><td align='right'><input type='submit' id='name_submit' value='Load Project'/></td></tr></table></form></center>";
var url_str="";var PAGE_PREV=-1;var PAGE_NEXT=-2;var PAGE_MORE=-3;function adjustIFrameHeight(){try{gadgets.window.adjustHeight()
}catch(A){}}function fetch(A,E,C,B){var D={};D[gadgets.io.RequestParameters.CONTENT_TYPE]=C;
if(B){D[gadgets.io.RequestParameters.NUM_ENTRIES]=B}gadgets.io.makeRequest(A,E,D)
}function fetchAsString(A,B){fetch(A,B,gadgets.io.ContentType.TEXT)}function fetchAsDom(A,B){fetch(A,B,gadgets.io.ContentType.DOM)
}function fetchAsFeed(A,C,B){fetch(A,C,gadgets.io.ContentType.FEED,B)}function fetchAsStringLegacy(A,B){fetchAsString(A,function(C){B(C.text)
})}function init(){$("#content_div").html("");
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
B++){words_arr[B]=ellipsify(words_arr[B],A)}return words_arr.join(" ")}var prefs_obj=new gadgets.Prefs();
var searchURL_tmpl="http://code.google.com/p/%PROJECT%/issues/list?can=1&q=%SEARCH%";var title_tmpl="%PROJECT% issues";
var urlMaster_tmpl="http://code.google.com/p/%PROJECT%/issues/list?can=1&sort=%SORT%&colspec=%COLSPEC%&num=%NUM%&start=%START%";
var invalidProject_tmpl="The project name, %PROJECT%, in the user preferences is invalid.";
var url_tmpl="";var projectName_str="";var sortBy_str="-modified";
var colspec_tmpl="ID+%SORTBY%+Summary";var colspec_str=sortBy_str.search("-")==-1?colspec_tmpl.replace("%SORTBY%",sortBy_str):colspec_tmpl.replace("%SORTBY%",sortBy_str.substring(1,sortBy_str.length));
var issueType_str=prefs_obj.getString("issueType");var issueData_arr=new Array();
var totalItems_str="";var userName_str=prefs_obj.getString("userName");if(userName_str==""&&(issueType_str=="assignedToMe"||issueType_str=="reportedByMe")){issueType_str="all"
}var filterSearch_bool=false;var filterSearch_str="";setFilteredSearch();var start_num=0;
var currentPage_num=1;var retrievedProjects_num=0;var otherProjects_str=_esc(prefs_obj.getString("otherProjects").toLowerCase());
var otherProjects_arr=otherProjects_str.split("%7C");var singleProject_bool=otherProjects_str=="";
var totalProjects_num=otherProjects_arr.length;function localInit(){retrievedProjects_num=0;
rebuildURL();init()}function rebuildURL(){url_tmpl=urlMaster_tmpl.replace("%SORT%",sortBy_str).replace("%COLSPEC%",colspec_str);
if(singleProject_bool){url_tmpl=url_tmpl.replace("%NUM%",10).replace("%START%",start_num)
}else{url_tmpl=url_tmpl.replace("%NUM%",41).replace("%START%",0)}if(filterSearch_bool){url_tmpl+=filterSearch_str
}}function render(A){issueData_arr=new Array();if(!singleProject_bool){for(var C=0;
C<totalProjects_num;C++){var B=url_tmpl.replace("%PROJECT%",otherProjects_arr[C]);
fetchAsStringLegacy(B,responseHandler)}}responseHandler(A,true)}function responseHandler(A,D){if(A.search(invalid_re)!=-1){var C=new gadgets.MiniMessage(moduleID_num);
C.createTimerMessage(invalidProject_tmpl.replace("%PROJECT%",scrapeInvalidProjectName(A)),5);
totalProjects_num--;return }if(D){var B=jQuery(".pagination:first",jQuery(A)).html();
totalItems_str=B==null?"0":new String(B.match(/.*of.*/)).replace(/.*of\ /,"")}if(A.search(/Your search did not generate any results./)==-1){var E=jQuery("#resultstable",jQuery(A));
scrapeContent(E,scrapeProjectName(A))}if(singleProject_bool){inject(A)}else{if(++retrievedProjects_num==(totalProjects_num+1)){inject("")
}}}function scrapeProjectName(B){var A=/<title>\s*[^\s]+\s*-\s*([^\s]+)/im;var C=B.match(A);
if(C.length==2){return C[1]}else{return""}}function scrapeInvalidProjectName(A){var B=A.search("/p/");
var C=A.search("/issues/");if(B==-1||C==-1){return""}B+=3;return A.substring(B,C)
}function inject(B){var D="";
var C="";C+=D;C+=buildContent();if(singleProject_bool){var A=generatePagingFromPage(B,start_num);
C+="<br />"+A}else{var F=Math.ceil(issueData_arr.length/10);F=F>4?4:F;var E=issueData_arr.length>40;
if(F>0){C+="<br />"+generatePaging(F,currentPage_num,E,totalItems_str)}}$("#content_div").html(C);
if(singleProject_bool){addPagingEvents(pagingCallbackSingle)}else{addPagingEvents(pagingCallbackMultiple)
}addSelectEvent();adjustIFrameHeight()}function scrapeContent(E,A){var B="";var C="";
var D="";E.find("tr").each(function(F){jQuery(this).find("td:not(:last):not(:first)").each(function(G){switch(G){case 0:B=jQuery(this).text();
break;case 1:C=jQuery(this).text();break;case 2:break;default:D=jQuery(this).text();
break}});if(B!=""&&D!=""){issueData_arr[issueData_arr.length++]=new issueData(C,B,D,A)
}})}function buildContent(){var B="<td valign='top'><a href='http://code.google.com/p/%PROJECT%/issues/detail?id=%ID%' target='_blank'>%ID%</a>%CONTENT%</td>";
var G="<td valign='top' style='white-space: nowrap; border-top: 1px solid #BBBBBB;'>%CONTENT%</td>";
var C="<td valign='top'>%CONTENT%</td>";var I="<td valign='top' style='border-top: 1px solid #BBBBBB;'><a href='http://code.google.com/p/%PROJECT%/issues/detail?id=%ID%' target='_blank'>%ID%</a>%CONTENT%</td>";
var A="<td valign='top'style='border-top: 1px solid #BBBBBB;'>%CONTENT%</td>";var D="";
var F;if(issueData_arr.length==0){return"There are no issues matching this query."
}if(sortBy_str=="-Opened"||sortBy_str=="-Modified"||sortBy_str=="-Closed"){issueData_arr.sort(sortIssueDataByDate)
}else{issueData_arr.sort(sortIssueData)}D+="<center><table cellspacing='0' cellpadding='0' width='100%' id='#resultstable' style='border-bottom: 1px solid #BBBBBB;'>";
var E=0;var H=issueData_arr.length;if(!singleProject_bool){E=(currentPage_num*10)-10;
H=currentPage_num*10;H=H<=issueData_arr.length?H:issueData_arr.length}for(F=E;F<H;
F++){D+="<tr>";if(!singleProject_bool){D+=G.replace("%CONTENT%",issueData_arr[F].sort_str.replace(/\ *ago/,""));
D+=G.replace("%CONTENT%",issueData_arr[F].projectName_str);D+="</tr><tr>";D+=B.replace("%PROJECT%",issueData_arr[F].projectName_str).replace("%ID%",issueData_arr[F].id_str).replace("%ID%",issueData_arr[F].id_str).replace("%CONTENT%","");
D+=C.replace("%CONTENT%",ellipsifyWords(issueData_arr[F].summary_str.replace(/[\n\r\ ]*$/,""),20))
}else{D+=I.replace("%PROJECT%",issueData_arr[F].projectName_str).replace("%ID%",issueData_arr[F].id_str).replace("%ID%",issueData_arr[F].id_str).replace("%CONTENT%","");
D+=G.replace("%CONTENT%",issueData_arr[F].sort_str.replace(/\ *ago/,""));D+=A.replace("%CONTENT%",ellipsifyWords(issueData_arr[F].summary_str.replace(/[\n\r\ ]*$/,""),20))
}D+="</tr>"}D+="</table></center>";return D}function pagingCallbackSingle(A){if(A==PAGE_MORE){moreURL_str=urlMaster_tmpl.replace("%SORT%",sortBy_str).replace("&colspec=%COLSPEC%","").replace("%START%",40).replace("&num=%NUM%","").replace("%PROJECT%",projectName_str);
window.open(moreURL_str,"_blank");return }if(A==PAGE_PREV){start_num-=10}else{if(A==PAGE_NEXT){start_num+=10
}else{start_num=(A-1)*10}}rebuildURL();init()}function pagingCallbackMultiple(A){if(A==PAGE_MORE){moreURL_str=urlMaster_tmpl.replace("%SORT%",sortBy_str).replace("&colspec=%COLSPEC%","").replace("%START%",0).replace("&num=%NUM%","").replace("%PROJECT%",projectName_str);
window.open(moreURL_str,"_blank");return }if(A==PAGE_PREV){currentPage_num--}else{if(A==PAGE_NEXT){currentPage_num++
}else{currentPage_num=A}}inject()}function addSelectEvent(){jQuery("#selectType").val(issueType_str);
$("#selectType").change(function(B){var C=jQuery(this).val();if(userName_str==""&&(C=="assignedToMe"||C=="reportedByMe")){var A=new gadgets.MiniMessage(moduleID_num);
A.createTimerMessage("To use this feature, please enter your user name in the preferences of this gadget.",4);
jQuery("#selectType").val(issueType_str)}else{issueType_str=C;prefs_obj.set("issueType",C);
setFilteredSearch();localInit()}})}function setFilteredSearch(){switch(issueType_str){case"all":filterSearch_bool=false;
break;case"starred":filterSearch_bool=true;filterSearch_str="&q=is%3Astarred";break;
case"assignedToMe":filterSearch_str="&q=owner%3A"+userName_str;filterSearch_bool=true;
break;case"reportedByMe":filterSearch_str="&q=reporter%3A"+userName_str;filterSearch_bool=true;
break}}function issueData(C,A,D,B){this.sort_str=C;this.id_str=A;this.summary_str=D;
this.projectName_str=B}function sortIssueData(B,A){var D=B.sort_str.toLowerCase();
var C=A.sort_str.toLowerCase();return((D<C)?-1:((D>C)?1:0))}function sortIssueDataByDate(B,A){var H=B.sort_str.toLowerCase();
var D=A.sort_str.toLowerCase();var E=rateDate(H);var F=rateDate(D);if(E==F){if(E==0){return 0
}var C=H.match(/[0-9]+/);var G=D.match(/[0-9]+/);if(C==G){return 0}if(Math.max(C,G)==C){return E>3?-1:1
}return E>3?1:-1}if(Math.max(E,F)==E){return 1}return -1}function rateDate(A){if(A.search(/moments/)!=-1){return 0
}if(A.search(/minutes/)!=-1){return 1}if(A.search(/hours/)!=-1){return 2}if(A.search(/days/)!=-1){return 3
}if(A.search(/[a-z]{3}\ [0-9]{2}$/)!=-1){return 4}if(A.search(/[a-z]{3}\ [0-9]{4}]/)!=-1){return 5
}return 6}gadgets.util.registerOnLoadHandler(localInit);
