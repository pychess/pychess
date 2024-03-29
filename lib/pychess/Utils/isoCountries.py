from collections import namedtuple

# https://www.iso.org/obp/ui/#iso:pub:PUB500001:en

ISO3166 = namedtuple("ISO3166", "iso2, country")
ISO3166_LIST = [
    ISO3166("unknown", _("Unknown")),
    # Specific to pyChess: ISO3166("C", _("Computer")),
    ISO3166("ad", _("Andorra")),
    ISO3166("ae", _("United Arab Emirates")),
    ISO3166("af", _("Afghanistan")),
    ISO3166("ag", _("Antigua and Barbuda")),
    ISO3166("ai", _("Anguilla")),
    ISO3166("al", _("Albania")),
    ISO3166("am", _("Armenia")),
    # Discontinued: ISO3166("an", _("Netherlands Antilles")),
    ISO3166("ao", _("Angola")),
    ISO3166("aq", _("Antarctica")),
    ISO3166("ar", _("Argentina")),
    ISO3166("as", _("American Samoa")),
    ISO3166("at", _("Austria")),
    ISO3166("au", _("Australia")),
    ISO3166("aw", _("Aruba")),
    ISO3166("ax", _("Åland Islands")),
    ISO3166("az", _("Azerbaijan")),
    ISO3166("ba", _("Bosnia and Herzegovina")),
    ISO3166("bb", _("Barbados")),
    ISO3166("bd", _("Bangladesh")),
    ISO3166("be", _("Belgium")),
    ISO3166("bf", _("Burkina Faso")),
    ISO3166("bg", _("Bulgaria")),
    ISO3166("bh", _("Bahrain")),
    ISO3166("bi", _("Burundi")),
    ISO3166("bj", _("Benin")),
    ISO3166("bl", _("Saint Barthélemy")),
    ISO3166("bm", _("Bermuda")),
    ISO3166("bn", _("Brunei Darussalam")),
    ISO3166("bo", _("Bolivia (Plurinational State of)")),
    ISO3166("bq", _("Bonaire, Sint Eustatius and Saba")),
    ISO3166("br", _("Brazil")),
    ISO3166("bs", _("Bahamas")),
    ISO3166("bt", _("Bhutan")),
    ISO3166("bv", _("Bouvet Island")),
    ISO3166("bw", _("Botswana")),
    ISO3166("by", _("Belarus")),
    ISO3166("bz", _("Belize")),
    ISO3166("ca", _("Canada")),
    ISO3166("cc", _("Cocos (Keeling) Islands")),
    ISO3166("cd", _("Congo (the Democratic Republic of the)")),
    ISO3166("cf", _("Central African Republic")),
    ISO3166("cg", _("Congo")),
    ISO3166("ch", _("Switzerland")),
    ISO3166("ci", _("Côte d'Ivoire")),
    ISO3166("ck", _("Cook Islands")),
    ISO3166("cl", _("Chile")),
    ISO3166("cm", _("Cameroon")),
    ISO3166("cn", _("China")),
    ISO3166("co", _("Colombia")),
    ISO3166("cr", _("Costa Rica")),
    ISO3166("cu", _("Cuba")),
    ISO3166("cv", _("Cabo Verde")),
    ISO3166("cw", _("Curaçao")),
    ISO3166("cx", _("Christmas Island")),
    ISO3166("cy", _("Cyprus")),
    ISO3166("cz", _("Czechia")),
    ISO3166("de", _("Germany")),
    ISO3166("dj", _("Djibouti")),
    ISO3166("dk", _("Denmark")),
    ISO3166("dm", _("Dominica")),
    ISO3166("do", _("Dominican Republic")),
    ISO3166("dz", _("Algeria")),
    ISO3166("ec", _("Ecuador")),
    ISO3166("ee", _("Estonia")),
    ISO3166("eg", _("Egypt")),
    ISO3166("eh", _("Western Sahara")),
    ISO3166("er", _("Eritrea")),
    ISO3166("es", _("Spain")),
    ISO3166("et", _("Ethiopia")),
    ISO3166("fi", _("Finland")),
    ISO3166("fj", _("Fiji")),
    ISO3166("fk", _("Falkland Islands [Malvinas]")),
    ISO3166("fm", _("Micronesia (Federated States of)")),
    ISO3166("fo", _("Faroe Islands")),
    ISO3166("fr", _("France")),
    ISO3166("ga", _("Gabon")),
    ISO3166("gb", _("United Kingdom of Great Britain and Northern Ireland")),
    ISO3166("gd", _("Grenada")),
    ISO3166("ge", _("Georgia")),
    ISO3166("gf", _("French Guiana")),
    ISO3166("gg", _("Guernsey")),
    ISO3166("gh", _("Ghana")),
    ISO3166("gi", _("Gibraltar")),
    ISO3166("gl", _("Greenland")),
    ISO3166("gm", _("Gambia")),
    ISO3166("gn", _("Guinea")),
    ISO3166("gp", _("Guadeloupe")),
    ISO3166("gq", _("Equatorial Guinea")),
    ISO3166("gr", _("Greece")),
    ISO3166("gs", _("South Georgia and the South Sandwich Islands")),
    ISO3166("gt", _("Guatemala")),
    ISO3166("gu", _("Guam")),
    ISO3166("gw", _("Guinea-Bissau")),
    ISO3166("gy", _("Guyana")),
    ISO3166("hk", _("Hong Kong")),
    ISO3166("hm", _("Heard Island and McDonald Islands")),
    ISO3166("hn", _("Honduras")),
    ISO3166("hr", _("Croatia")),
    ISO3166("ht", _("Haiti")),
    ISO3166("hu", _("Hungary")),
    ISO3166("id", _("Indonesia")),
    ISO3166("ie", _("Ireland")),
    ISO3166("il", _("Israel")),
    ISO3166("im", _("Isle of Man")),
    ISO3166("in", _("India")),
    ISO3166("io", _("British Indian Ocean Territory")),
    ISO3166("iq", _("Iraq")),
    ISO3166("ir", _("Iran (Islamic Republic of)")),
    ISO3166("is", _("Iceland")),
    ISO3166("it", _("Italy")),
    ISO3166("je", _("Jersey")),
    ISO3166("jm", _("Jamaica")),
    ISO3166("jo", _("Jordan")),
    ISO3166("jp", _("Japan")),
    ISO3166("ke", _("Kenya")),
    ISO3166("kg", _("Kyrgyzstan")),
    ISO3166("kh", _("Cambodia")),
    ISO3166("ki", _("Kiribati")),
    ISO3166("km", _("Comoros")),
    ISO3166("kn", _("Saint Kitts and Nevis")),
    ISO3166("kp", _("Korea (the Democratic People's Republic of)")),
    ISO3166("kr", _("Korea (the Republic of)")),
    ISO3166("kw", _("Kuwait")),
    ISO3166("ky", _("Cayman Islands")),
    ISO3166("kz", _("Kazakhstan")),
    ISO3166("la", _("Lao People's Democratic Republic")),
    ISO3166("lb", _("Lebanon")),
    ISO3166("lc", _("Saint Lucia")),
    ISO3166("li", _("Liechtenstein")),
    ISO3166("lk", _("Sri Lanka")),
    ISO3166("lr", _("Liberia")),
    ISO3166("ls", _("Lesotho")),
    ISO3166("lt", _("Lithuania")),
    ISO3166("lu", _("Luxembourg")),
    ISO3166("lv", _("Latvia")),
    ISO3166("ly", _("Libya")),
    ISO3166("ma", _("Morocco")),
    ISO3166("mc", _("Monaco")),
    ISO3166("md", _("Moldova (the Republic of)")),
    ISO3166("me", _("Montenegro")),
    ISO3166("mf", _("Saint Martin (French part)")),
    ISO3166("mg", _("Madagascar")),
    ISO3166("mh", _("Marshall Islands")),
    ISO3166("mk", _("Macedonia (the former Yugoslav Republic of)")),
    ISO3166("ml", _("Mali")),
    ISO3166("mm", _("Myanmar")),
    ISO3166("mn", _("Mongolia")),
    ISO3166("mo", _("Macao")),
    ISO3166("mp", _("Northern Mariana Islands")),
    ISO3166("mq", _("Martinique")),
    ISO3166("mr", _("Mauritania")),
    ISO3166("ms", _("Montserrat")),
    ISO3166("mt", _("Malta")),
    ISO3166("mu", _("Mauritius")),
    ISO3166("mv", _("Maldives")),
    ISO3166("mw", _("Malawi")),
    ISO3166("mx", _("Mexico")),
    ISO3166("my", _("Malaysia")),
    ISO3166("mz", _("Mozambique")),
    ISO3166("na", _("Namibia")),
    ISO3166("nc", _("New Caledonia")),
    ISO3166("ne", _("Niger")),
    ISO3166("nf", _("Norfolk Island")),
    ISO3166("ng", _("Nigeria")),
    ISO3166("ni", _("Nicaragua")),
    ISO3166("nl", _("Netherlands")),
    ISO3166("no", _("Norway")),
    ISO3166("np", _("Nepal")),
    ISO3166("nr", _("Nauru")),
    ISO3166("nu", _("Niue")),
    ISO3166("nz", _("New Zealand")),
    ISO3166("om", _("Oman")),
    ISO3166("pa", _("Panama")),
    ISO3166("pe", _("Peru")),
    ISO3166("pf", _("French Polynesia")),
    ISO3166("pg", _("Papua New Guinea")),
    ISO3166("ph", _("Philippines")),
    ISO3166("pk", _("Pakistan")),
    ISO3166("pl", _("Poland")),
    ISO3166("pm", _("Saint Pierre and Miquelon")),
    ISO3166("pn", _("Pitcairn")),
    ISO3166("pr", _("Puerto Rico")),
    ISO3166("ps", _("Palestine, State of")),
    ISO3166("pt", _("Portugal")),
    ISO3166("pw", _("Palau")),
    ISO3166("py", _("Paraguay")),
    ISO3166("qa", _("Qatar")),
    ISO3166("re", _("Réunion")),
    ISO3166("ro", _("Romania")),
    ISO3166("rs", _("Serbia")),
    ISO3166("ru", _("Russian Federation")),
    ISO3166("rw", _("Rwanda")),
    ISO3166("sa", _("Saudi Arabia")),
    ISO3166("sb", _("Solomon Islands")),
    ISO3166("sc", _("Seychelles")),
    ISO3166("sd", _("Sudan")),
    ISO3166("se", _("Sweden")),
    ISO3166("sg", _("Singapore")),
    ISO3166("sh", _("Saint Helena, Ascension and Tristan da Cunha")),
    ISO3166("si", _("Slovenia")),
    ISO3166("sj", _("Svalbard and Jan Mayen")),
    ISO3166("sk", _("Slovakia")),
    ISO3166("sl", _("Sierra Leone")),
    ISO3166("sm", _("San Marino")),
    ISO3166("sn", _("Senegal")),
    ISO3166("so", _("Somalia")),
    ISO3166("sr", _("Suriname")),
    ISO3166("ss", _("South Sudan")),
    ISO3166("st", _("Sao Tome and Principe")),
    ISO3166("sv", _("El Salvador")),
    ISO3166("sx", _("Sint Maarten (Dutch part)")),
    ISO3166("sy", _("Syrian Arab Republic")),
    ISO3166("sz", _("Eswatini")),
    ISO3166("tc", _("Turks and Caicos Islands")),
    ISO3166("td", _("Chad")),
    ISO3166("tf", _("French Southern Territories")),
    ISO3166("tg", _("Togo")),
    ISO3166("th", _("Thailand")),
    ISO3166("tj", _("Tajikistan")),
    ISO3166("tk", _("Tokelau")),
    ISO3166("tl", _("Timor-Leste")),
    ISO3166("tm", _("Turkmenistan")),
    ISO3166("tn", _("Tunisia")),
    ISO3166("to", _("Tonga")),
    # Discontinued: ISO3166("tp", _("East Timor")),
    ISO3166("tr", _("Turkey")),
    ISO3166("tt", _("Trinidad and Tobago")),
    ISO3166("tv", _("Tuvalu")),
    ISO3166("tw", _("Taiwan (Province of China)")),
    ISO3166("tz", _("Tanzania, United Republic of")),
    ISO3166("ua", _("Ukraine")),
    ISO3166("ug", _("Uganda")),
    ISO3166("um", _("United States Minor Outlying Islands")),
    ISO3166("us", _("United States of America")),
    ISO3166("uy", _("Uruguay")),
    ISO3166("uz", _("Uzbekistan")),
    ISO3166("va", _("Holy See")),
    ISO3166("vc", _("Saint Vincent and the Grenadines")),
    ISO3166("ve", _("Venezuela (Bolivarian Republic of)")),
    ISO3166("vg", _("Virgin Islands (British)")),
    ISO3166("vi", _("Virgin Islands (U.S.)")),
    ISO3166("vn", _("Viet Nam")),
    ISO3166("vu", _("Vanuatu")),
    ISO3166("wf", _("Wallis and Futuna")),
    ISO3166("ws", _("Samoa")),
    ISO3166("ye", _("Yemen")),
    ISO3166("yt", _("Mayotte")),
    # Discontinued: ISO3166("yu", _("Yugoslavia")),
    ISO3166("za", _("South Africa")),
    ISO3166("zm", _("Zambia")),
    ISO3166("zw", _("Zimbabwe")),
]

# Bubble sort for the translated countries
for i in range(len(ISO3166_LIST) - 1, 1, -1):
    for j in range(1, i - 1):
        if ISO3166_LIST[i].country < ISO3166_LIST[j].country:
            tmp = ISO3166_LIST[i]
            ISO3166_LIST[i] = ISO3166_LIST[j]
            ISO3166_LIST[j] = tmp
