#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BMB 2026-06-24
# Centralized country name → ISO A3 lookup for Python scripts. Single source of truth
# for country normalization across the pipeline. See also country_mapping.R.

import re
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Comprehensive country name to ISO A3 code mapping (973 variants -> 240 ISO codes)
COUNTRY_TO_ISO = {
    "canada": "CAN",
    "canada western": "CAN",
    "western canada": "CAN",
    "eastern canada": "CAN",
    "united states": "USA",
    "mexico": "MEX",
    "guatemala": "GTM",
    "belize": "BLZ",
    "honduras": "HND",
    "el salvador": "SLV",
    "nicaragua": "NIC",
    "costa rica": "CRI",
    "panama": "PAN",
    "colombia": "COL",
    "antioquia": "COL",
    "venezuela": "VEN",
    "guyana": "GUY",
    "suriname": "SUR",
    "french guiana": "GUF",
    "argentina": "ARG",
    "new caledonia": "NCL",
    "brazil": "BRA",
    "chile": "CHL",
    "southern chile": "CHL",
    "peru": "PER",
    "ecuador": "ECU",
    "paraguay": "PRY",
    "uruguay": "URY",
    "bolivia": "BOL",
    "jamaica": "JAM",
    "dominican republic": "DOM",
    "haiti": "HTI",
    "cuba": "CUB",
    "puerto rico": "PRI",
    "trinidad and tobago": "TTO",
    "bahamas": "BHS",
    "barbados": "BRB",
    "grenada": "GRD",
    "saint lucia": "LCA",
    "saint vincent and the grenadines": "VCT",
    "antigua and barb.": "ATG",
    "antigua and barbuda": "ATG",
    "dominica": "DMA",
    "saint kitts and nevis": "KNA",
    "nova scotia": "CAN",
    "british columbia": "CAN",
    "viçosa": "BRA",
    "eastern canada": "CAN",
    "new brunswick": "CAN",
    "united kingdom": "GBR",
    "ireland": "IRL",
    "france": "FRA",
    "germany": "DEU",
    "italy": "ITA",
    "sicily": "ITA",
    "sardinia": "ITA",
    "lombardy": "ITA",
    "tuscany": "ITA",
    "spain": "ESP",
    "canary": "ESP",
    "portugal": "PRT",
    "netherlands": "NLD",
    "belgium": "BEL",
    "luxembourg": "LUX",
    "switzerland": "CHE",
    "swiss jura mountains": "CHE",
    "austria": "AUT",
    "czech republic": "CZE",
    "slovakia": "SVK",
    "slovenia": "SVN",
    "croatia": "HRV",
    "bosnia and herzegovina": "BIH",
    "serbia": "SRB",
    "montenegro": "MNE",
    "macedonia": "MKD",
    "kosovo": "XKX",
    "albania": "ALB",
    "greece": "GRC",
    "romania": "ROU",
    "malta": "MLT",
    "bulgaria": "BGR",
    "hungary": "HUN",
    "poland": "POL",
    "ukraine": "UKR",
    "belarus": "BLR",
    "russia": "RUS",
    "russian far east": "RUS",
    "moldova": "MDA",
    "latvia": "LVA",
    "lithuania": "LTU",
    "estonia": "EST",
    "denmark": "DNK",
    "sweden": "SWE",
    "norway": "NOR",
    "finland": "FIN",
    "iceland": "ISL",
    "northern ireland": "GBR",
    "scotland": "GBR",
    "wales": "GBR",
    "england": "GBR",
    "britain": "GBR",
    "the netherlands": "NLD",
    "svalbard": "NOR",
    "greenland": "GRL",
    "faroe": "FRO",
    "faroe islands": "FRO",
    "great britain": "GBR",
    "gomera": "ESP",
    "egypt": "EGY",
    "benin": "BEN",
    "libya": "LBY",
    "algeria": "DZA",
    "tamanghasset": "DZA",
    "tunisia": "TUN",
    "msila": "DZA",
    "el-haourane": "DZA",
    "morocco": "MAR",
    "south africa": "ZAF",
    "transkei": "ZAF",
    "southern transkei": "ZAF",
    "namibia": "NAM",
    "botswana": "BWA",
    "zimbabwe": "ZWE",
    "zambia": "ZMB",
    "malawi": "MWI",
    "mozambique": "MOZ",
    "tanzania": "TZA",
    "kenya": "KEN",
    "uganda": "UGA",
    "rwanda": "RWA",
    "burundi": "BDI",
    "congo": "COG",
    "democratic republic of congo": "COD",
    "cameroon": "CMR",
    "central african republic": "CAF",
    "gabon": "GAB",
    "equatorial guinea": "GNQ",
    "nigeria": "NGA",
    "niger": "NER",
    "ghana": "GHA",
    "ivory coast": "CIV",
    "côte d'ivoire": "CIV",
    "burkina faso": "BFA",
    "mali": "MLI",
    "mauritania": "MRT",
    "senegal": "SEN",
    "gambia": "GMB",
    "guinea-bissau": "GNB",
    "guinea": "GIN",
    "sierra leone": "SLE",
    "liberia": "LBR",
    "ethiopia": "ETH",
    "somalia": "SOM",
    "djibouti": "DJI",
    "eritrea": "ERI",
    "sudan": "SDN",
    "south sudan": "SSD",
    "chad": "TCD",
    "mauritius": "MUS",
    "madagascar": "MDG",
    "seychelles": "SYC",
    "china": "CHN",
    "anhui huoshan": "CHN",
    "of yunnan": "CHN",
    "anhui": "CHN",
    "southwestern china": "CHN",
    "qinghai-tibet plateau": "CHN",
    "qinghai-tibet": "CHN",
    "qinghai tibet": "CHN",
    "north china": "CHN",
    "south china": "CHN",
    "east china": "CHN",
    "west china": "CHN",
    "southern china": "CHN",
    "southeast china": "CHN",
    "southwest china": "CHN",
    "people's republic of china": "CHN",
    "peoples republic of china": "CHN",
    "prc": "CHN",
    "trinidad": "TTO",
    "trinidad and tobago": "TTO",
    "pr china": "CHN",
    "p r china": "CHN",
    "taiwan": "TWN",
    "formosa": "TWN",
    "formosan": "TWN",
    "hong kong": "HKG",
    "macau": "MAC",
    "japan": "JPN",
    "south korea": "KOR",
    "korea": "KOR",
    "north korea": "PRK",
    "mongolia": "MNG",
    "afghanistan": "AFG",
    "pakistan": "PAK",
    "india": "IND",
    "chhattisgarh": "IND",
    "central india": "IND",
    "arunachal pradesh": "IND",
    "tripura": "IND",
    "south east india": "IND",
    "north-east india": "IND",
    "northeast india": "IND",
    "bangladesh": "BGD",
    "nepal": "NPL",
    "bhutan": "BTN",
    "sri lanka": "LKA",
    "myanmar": "MMR",
    "thailand": "THA",
    "northern thailand": "THA",
    "thai": "THA",
    "laos": "LAO",
    "cambodia": "KHM",
    "vietnam": "VNM",
    "philippines": "PHL",
    "indonesia": "IDN",
    "malaysia": "MYS",
    "west malaysia": "MYS",
    "peninsular malaysia": "MYS",
    "singapore": "SGP",
    "brunei": "BRN",
    "brunei darussalam": "BRN",
    "east timor": "TLS",
    "timor-leste": "TLS",
    "papua new guinea": "PNG",
    "yemen": "YEM",
    "oman": "OMN",
    "united arab emirates": "ARE",
    "qatar": "QAT",
    "bahrain": "BHR",
    "kuwait": "KWT",
    "saudi arabia": "SAU",
    "saudi-arabia": "SAU",
    "iraq": "IRQ",
    "iran": "IRN",
    "turkey": "TUR",
    "türkiye": "TUR",
    "syria": "SYR",
    "lebanon": "LBN",
    "israel": "ISR",
    "palestine": "PSE",
    "cyprus": "CYP",
    "kazakhstan": "KAZ",
    "uzbekistan": "UZB",
    "turkmenistan": "TKM",
    "tajikistan": "TJK",
    "kyrgyzstan": "KGZ",
    "australia": "AUS",
    "new zealand": "NZL",
    "aotearoa": "NZL",
    "fiji": "FJI",
    "samoa": "WSM",
    "vanuatu": "VUT",
    "solomon islands": "SLB",
    "micronesia": "FSM",
    "palau": "PLW",
    "marshall islands": "MHL",
    "kiribati": "KIR",
    "tuvalu": "TUV",
    "nauru": "NRU",
    "new south wales": "AUS",
    "yunnan": "CHN",
    "qinghai": "CHN",
    "jiangxi": "CHN",
    "gansu": "CHN",
    "nei mongol": "CHN",
    "inner mongolia": "CHN",
    "sichuan": "CHN",
    "hainan": "CHN",
    "xinjiang": "CHN",
    "zhejiang": "CHN",
    "xuwen": "CHN",
    "guangdong": "CHN",
    "fujian": "CHN",
    "guangxi": "CHN",
    "beijing": "CHN",
    "shanghai": "CHN",
    "liaoning": "CHN",
    "jilin": "CHN",
    "heilongjiang": "CHN",
    "tibet": "CHN",
    "fuyang": "CHN",
    "guizhou": "CHN",
    "zhanjiang": "CHN",
    "sumatra": "IDN",
    "java": "IDN",
    "borneo": "IDN",
    "jeddah": "SAU",
    "goa": "IND",
    "west bengal": "IND",
    "tamil nadu": "IND",
    "tamil naidu": "IND",
    "chennai": "IND",
    "mandi district": "IND",
    "himachal pradesh": "IND",
    "nashik": "IND",
    "himalaya": "IND",
    "rajasthan": "IND",
    "mumbai": "IND",
    "delhi": "IND",
    "new delhi": "IND",
    "bangalore": "IND",
    "hyderabad": "IND",
    "tamilnadu": "IND",
    "karnataka": "IND",
    "haryana": "IND",
    "uttarakhand": "IND",
    "uttarpradesh": "IND",
    "odisha": "IND",
    "manipur": "IND",
    "salem": "IND",
    "yercaud": "IND",
    "yercaud hills": "IND",
    "nashik district": "IND",
    "maharashtra": "IND",
    "assam": "IND",
    "kerala": "IND",
    "punjab": "IND",
    "uttar pradesh": "IND",
    "andhra pradesh": "IND",
    "andhra": "IND",
    "bombay": "IND",
    "telangana": "IND",
    "bengkulu": "IDN",
    "southern india": "IND",
    "meghalaya": "IND",
    "ne india": "IND",
    "northeastern india": "IND",
    "northern india": "IND",
    "northwestern india": "IND",
    "northeast india": "IND",
    "gujarati": "IND",
    "garhwal": "IND",
    "haridwar": "IND",
    "jammu kashmir": "IND",
    "khammam": "IND",
    "kodiyakarai": "IND",
    "kollam": "IND",
    "mandi": "IND",
    "mymensingh": "IND",
    "puducherry": "IND",
    "uttrakhand": "IND",
    "tamilnadu state": "IND",
    "karnataka state": "IND",
    "kalimantan": "IDN",
    "sulawesi": "IDN",
    "sarawak": "MYS",
    "johor": "MYS",
    "penang": "MYS",
    "peninsular malaysia": "MYS",
    "bahia state": "BRA",
    "minas gerais": "BRA",
    "sao paulo": "BRA",
    "rio grande do sul state": "BRA",
    "santa catarina state": "BRA",
    "corsica": "FRA",
    "madeira": "PRT",
    "la reunion": "FRA",
    "martinique": "MTQ",
    "tahiti": "PYF",
    "moorea": "PYF",
    "tenerife": "ESP",
    "la palma": "ESP",
    "majorca": "ESP",
    "balearic": "ESP",
    "alicante": "ESP",
    "palencia": "ESP",
    "samsun": "TUR",
    "hormozgan": "IRN",
    "qena governorate": "EGY",
    "upper egypt": "EGY",
    "azerbaijan": "AZE",
    "primorsky": "RUS",
    "moscow oblast": "RUS",
    "amur": "RUS",
    "belorussian ssr": "BLR",
    "republic of moldova": "MDA",
    "shetland": "GBR",
    "shetlands": "GBR",
    "isle of man": "GBR",
    "flanders": "BEL",
    "alentejo": "PRT",
    "lisbon": "PRT",
    "tashkent": "UZB",
    "ulsan city": "KOR",
    "ibaraki": "JPN",
    "satakunta": "FIN",
    "ny-ålesund": "NOR",
    "spitsbergen": "NOR",
    "togo": "TGO",
    "comoros": "COM",
    "timor": "TLS",
    "timor leste": "TLS",
    "papua": "PNG",
    "falkland islands": "FLK",
    "ny aalesund": "NOR",
    "american samoa": "USA",
    "hawaii": "USA",
    "arizona": "USA",
    "arkansas": "USA",
    "california": "USA",
    "florida": "USA",
    "texas": "USA",
    "new york": "USA",
    "idaho": "USA",
    "alaska": "USA",
    "ohio": "USA",
    "pennsylvania": "USA",
    "michigan": "USA",
    "north carolina": "USA",
    "virginia": "USA",
    "oregon": "USA",
    "washington": "USA",
    "massachusetts": "USA",
    "illinois": "USA",
    "indiana": "USA",
    "iowa": "USA",
    "carolina": "USA",
    "south carolina": "USA",
    "kentucky": "USA",
    "maryland": "USA",
    "mississippi": "USA",
    "missouri": "USA",
    "connecticut": "USA",
    "dakota": "USA",
    "delaware": "USA",
    "louisiana": "USA",
    "new jersey": "USA",
    "new mexico": "USA",
    "oklahoma": "USA",
    "alabama": "USA",
    "maine": "USA",
    "minnesota": "USA",
    "nebraska": "USA",
    "kansas": "USA",
    "western australia": "AUS",
    "south australia": "AUS",
    "victoria": "AUS",
    "tasmania": "AUS",
    "queensland": "AUS",
    "eastern australia": "AUS",
    "southwestern australia": "AUS",
    "south-western australia": "AUS",
    "northern territory": "AUS",
    "northern territory of australia": "AUS",
    "usa": "USA",
    "new-zealand": "NZL",
    "brasil": "BRA",
    "burma": "MMR",
    "cameroun": "CMR",
    "french polynesia": "PYF",
    "republic of panama": "PAN",
    "russian federation": "RUS",
    "the peoples republic of china": "CHN",
    "federal republic of germany": "DEU",
    "ksa": "SAU",
    "ontario": "CAN",
    "alberta": "CAN",
    "manitoba": "CAN",
    "quebec": "CAN",
    "canada western canada": "CAN",
    "antarctica": "ATA",
    "antarctic": "ATA",
    "lagotellerie": "ATA",
    "moutonné valley on alexander island": "ATA",
    "east antarctica": "ATA",
    "east continental antarctica": "ATA",
    "south antarctica": "ATA",
    "central transantarctic mountains": "ATA",
    "moutonné valley on alexander": "ATA",
    "transantarctic mountains": "ATA",
    "king george": "ATA",
    "king george island": "ATA",
    "angola": "AGO",
    "jordan": "JOR",
    "maritime antarctica": "ATA",
    "rhynie": "GBR",
    "bermuda": "BMU",
    "bosnia": "BIH",
    "herzegovina": "BIH",
    "newfoundland": "CAN",
    "la réunion": "REU",
    "cote divoire": "CIV",
    "côte divoire": "CIV",
    "yugoslavia": "SRB",
    "bicol": "PHL",
    "southern italy": "ITA",
    "parts of italy": "ITA",
    "dutch": "NLD",
    "east india": "IND",
    "finnish": "FIN",
    "korean": "KOR",
    "northern spain": "ESP",
    "central spain": "ESP",
    "british-columbia": "CAN",
    "brunswick": "CAN",
    "buenos aires": "ARG",
    "canadian": "CAN",
    "chiapas": "MEX",
    "colorado": "USA",
    "cordoba": "ARG",
    "cuneo": "ITA",
    "gujarat": "IND",
    "jalisco": "MEX",
    "kashmir": "IND",
    "paraná": "BRA",
    "patagonia": "ARG",
    "peruvian amazon": "PER",
    "sinaloa": "MEX",
    "southeastern brazil": "BRA",
    "southern france": "FRA",
    "southern morocco": "MAR",
    "southern poland": "POL",
    "veracruz": "MEX",
    "western montana": "USA",
    "western oregon": "USA",
    "akmola": "KAZ",
    "alberta rocky mountains": "CAN",
    "andaman": "IND",
    "apulia": "ITA",
    "baise": "CHN",
    "bangi": "CAF",
    "bisle ghat": "IND",
    "british": "GBR",
    "campina grande": "BRA",
    "cear? state": "BRA",
    "chengde": "CHN",
    "chenzhou": "CHN",
    "chikwawa": "MWI",
    "chilean southern andes": "CHL",
    "cianjur": "IDN",
    "cili country": "CHN",
    "columbia basin": "USA",
    "egyptian": "EGY",
    "french pyrenees": "FRA",
    "gannan": "CHN",
    "german": "DEU",
    "germany berlin": "DEU",
    "guizhou dushan": "CHN",
    "hexi": "CHN",
    "hitachi mine": "JPN",
    "hull": "GBR",
    "inner mengolia": "CHN",
    "inner mongolia of northern china": "CHN",
    "people’s republic of china": "CHN",
    "ningxia": "CHN",
    "central panama": "PAN",
    "central spain": "ESP",
    "hainan island": "CHN",
    "south india": "IND",
    "jammu & kashmir": "IND",
    "korean ecotype": "KOR",
    "lueyang country": "CHN",
    "mala y sia": "MYS",
    "malay": "MYS",
    "min county": "CHN",
    "minqin of gansu": "CHN",
    "minxian": "CHN",
    "monte azul": "BRA",
    "ningxia hui autonomous region of china": "CHN",
    "north-west china": "CHN",
    "north-west tasmania": "AUS",
    "north-western himalaya": "IND",
    "northern china": "CHN",
    "northern finland": "FIN",
    "aland": "FIN",
    "northern germany": "DEU",
    "northern mexico": "MEX",
    "northern pennsylvania": "USA",
    "northwestern himalayas": "IND",
    "panan": "CHN",
    "pauri": "IND",
    "pingjiang": "CHN",
    "qilian mountain": "CHN",
    "qinghai-tibetan plateau": "CHN",
    "qinghai-xizang": "CHN",
    "qinghai-xizang plateau": "CHN",
    "río negro": "ARG",
    "san luis": "ARG",
    "shapotou of ningxia": "CHN",
    "south-east queensland": "AUS",
    "south-eastern england": "GBR",
    "south-west britain": "GBR",
    "south-west china": "CHN",
    "southeastern queensland": "AUS",
    "southern bahia state": "BRA",
    "southern kyushu": "JPN",
    "tatra mountains": "SVK",
    "te anau": "NZL",
    "tibetan autonomous": "CHN",
    "tierra del fuego": "ARG",
    "tongren city": "CHN",
    "wenxian": "CHN",
    "western alps": "ITA",
    "western anatolia": "TUR",
    "western hubei": "CHN",
    "western siberia": "RUS",
    "willamette valley": "USA",
    "xiongan new area": "CHN",
    "yinchuan": "CHN",
    "yinjing": "CHN",
    "yunnan menglian": "CHN",
    "yuqian": "CHN",
    "zhuhai": "CHN",
    "zhuhai city": "CHN",
    "zunyi country": "CHN",
    "continental antarctica": "ATA",
    "coast of india": "IND",
    "county in barinas": "VEN",
    "district udhampur in jammu division": "IND",
    "dongxiang": "CHN",
    "gurbantunggut desert": "CHN",
    "including china": "CHN",
    "india/bangladesh": "IND",
    "india/bangladesh": "BGD",
    "southern iberian": "ESP",
    "southern iberian": "PRT",
    "rkiye": "TUR",
    "tü": "TUR",
    "ind": "IND",
    "greenland": "GRL",
    "iceland": "ISL",
    "mississippi river basin": "USA",
    "svalbard": "NOR",
    "franz josef land": "RUS",
    "new siberian islands": "RUS",
    "novaya zemlya": "RUS",
    "macdonnell ranges": "AUS",
    "brazilian highlands": "BRA",
    "guiana highlands": "GUY",
    "são tomé and príncipe": "STP",
    "canadian arctic archipelago": "CAN",
    "ural mountains": "RUS",
    "severnaya zemlya": "RUS",
    "wrangel island": "RUS",
    "great lakes": "USA",
    "great lakes": "CAN",
    "hudson bay": "CAN",
    "sierra madre oriental": "MEX",
    "sierra madre occidental": "MEX",
    "sierra madre del sur": "MEX",
    "trans-mexican volcanic belt": "MEX",
    "sonoran desert": "USA",
    "sonoran desert": "MEX",
    "mojave desert": "USA",
    "chihuahuan desert": "USA",
    "chihuahuan desert": "MEX",
    "great basin desert": "USA",
    "colorado plateau": "USA",
    "rocky mountains": "USA",
    "rocky mountains": "CAN",
    "appalachian mountains": "USA",
    "appalachian mountains": "CAN",
    "sierra nevada": "USA",
    "cascade range": "USA",
    "cascade range": "CAN",
    "coast ranges": "USA",
    "coast ranges": "CAN",
    "great plains": "USA",
    "great plains": "CAN",
    "central valley": "USA",
    "juan fernández islands": "CHL",
    "desventuradas islands": "CHL",
    "magellanic subpolar forests": "CHL",
    "magellanic subpolar forests": "ARG",
    "valdivian temperate rain forest": "CHL",
    "valdivian temperate rain forest": "ARG",
    "patagonian steppe": "ARG",
    "patagonian steppe": "CHL",
    "pampas": "ARG",
    "pampas": "URY",
    "pampas": "BRA",
    "gran chaco": "ARG",
    "gran chaco": "BOL",
    "gran chaco": "PRY",
    "gran chaco": "BRA",
    "atlantic forest": "BRA",
    "atlantic forest": "ARG",
    "atlantic forest": "PRY",
    "cerrado": "BRA",
    "cerrado": "BOL",
    "cerrado": "PRY",
    "caatinga": "BRA",
    "yungas": "BOL",
    "yungas": "PER",
    "yungas": "ARG",
    "puna": "ARG",
    "puna": "BOL",
    "puna": "CHL",
    "puna": "PER",
    "paramo": "COL",
    "paramo": "ECU",
    "paramo": "PER",
    "paramo": "VEN",
    "atacama": "CHL",
    "maule": "CHL",
    "santiago": "CHL",
    "coquimbo": "CHL",
    "monte": "ARG",
    "espinal": "ARG",
    "tumbes-chocó-magdalena": "COL",
    "tumbes-chocó-magdalena": "ECU",
    "tumbes-chocó-magdalena": "PAN",
    "tumbes-chocó-magdalena": "PER",
    "chocó-darién": "COL",
    "chocó-darién": "PAN",
    "panamanian": "PAN",
    "sino-japanese": "CHN",
    "sino-japanese": "JPN",
    "sundanian": "IDN",
    "sundanian": "MYS",
    "sundanian": "BRN",
    "wallacean": "IDN",
    "philippine": "PHL",
    "sundaland": "IDN",
    "sundaland": "MYS",
    "sundaland": "BRN",
    "sundaland": "SGP",
    "sundaland": "THA",
    "wallacea": "IDN",
    "beringia": "RUS",
    "beringia": "USA",
    "himalayas": "NPL",
    "himalayas": "BTN",
    "himalayas": "IND",
    "himalayas": "CHN",
    "himalayas": "PAK",
    "tibetan plateau": "CHN",
    "kunlun mountains": "CHN",
    "tian shan": "CHN",
    "tian shan": "KAZ",
    "tian shan": "KGZ",
    "tian shan": "UZB",
    "altai mountains": "RUS",
    "altai mountains": "CHN",
    "altai mountains": "MNG",
    "altai mountains": "KAZ",
    "sayan mountains": "MNG",
    "sayan mountains": "RUS",
    "stanovoy range": "RUS",
    "verkhoyansk range": "RUS",
    "chersky range": "RUS",
    "kolyma mountains": "RUS",
    "sikhote-alin": "RUS",
    "zagros mountains": "IRN",
    "zagros mountains": "IRQ",
    "zagros mountains": "TUR",
    "taurus mountains": "TUR",
    "pontic mountains": "TUR",
    "anatolian plateau": "TUR",
    "iranian plateau": "IRN",
    "iranian plateau": "AFG",
    "iranian plateau": "PAK",
    "armenian highlands": "ARM",
    "armenian highlands": "TUR",
    "armenian highlands": "IRN",
    "armenian highlands": "AZE",
    "armenian highlands": "GEO",
    "ethiopian highlands": "ETH",
    "ethiopian highlands": "ERI",
    "drakensberg": "ZAF",
    "drakensberg": "LSO",
    "atlas mountains": "MAR",
    "atlas mountains": "DZA",
    "atlas mountains": "TUN",
    "ahaggar mountains": "DZA",
    "tibesti mountains": "TCD",
    "tibesti mountains": "LBY",
    "guinea highlands": "GIN",
    "guinea highlands": "SLE",
    "guinea highlands": "LBR",
    "guinea highlands": "CIV",
    "cameroon highlands": "CMR",
    "cameroon highlands": "NGA",
    "australian alps": "AUS",
    "great dividing range": "AUS",
    "kimberley": "AUS",
    "hamersley range": "AUS",
    "darling range": "AUS",
    "new guinea highlands": "IDN",
    "new guinea highlands": "PNG",
    "southern alps": "NZL",
    "hawaiian islands": "USA",
    "galapagos islands": "ECU",
    "canary islands": "ESP",
    "azores": "PRT",
    "cape verde": "CPV",
    "maldives": "MDV",
    "chagos archipelago": "IOT",
    "andaman islands": "IND",
    "nicobar islands": "IND",
    "lakshadweep": "IND",
    "new guinea": "IDN",
    "new guinea": "PNG",
    "sakhalin": "RUS",
    "kuril islands": "RUS",
    "aleutian islands": "USA",
    "south georgia and the south sandwich islands": "SGS",
    "bouvet island": "BVT",
    "heard island and mcdonald islands": "HMD",
    "kermadec islands": "NZL",
    "chatham islands": "NZL",
    "auckland islands": "NZL",
    "campbell island": "NZL",
    "antipodes islands": "NZL",
    "bounty islands": "NZL",
    "snares islands": "NZL",
    "macquarie island": "AUS",
    "tonga": "TON",
    "cook islands": "COK",
    "pitcairn islands": "PCN",
    "easter island": "CHL",
    "saint helena, ascension and tristan da cunha": "SHN",
    "andorra": "AND",
    "anguilla": "AIA",
    "armenia": "ARM",
    "aruba": "ABW",
    "br. indian ocean ter.": "IOT",
    "br indian ocean ter": "IOT",
    "british indian ocean": "IOT",
    "british virgin is.": "VGB",
    "cayman is.": "CYM",
    "curaçao": "CUW",
    "dem. rep. korea": "PRK",
    "eq. guinea": "GNQ",
    "fr. s. antarctic lands": "ATF",
    "fr s antarctic lands": "ATF",
    "french s antarctic lands": "ATF",
    "gambia": "GMB",
    "georgia": "GEO",
    "guam": "GUM",
    "guernsey": "GGY",
    "jersey": "JEY",
    "lesotho": "LSO",
    "liechtenstein": "LIE",
    "macao": "MAC",
    "monaco": "MCO",
    "montserrat": "MSR",
    "n. mariana is.": "MNP",
    "norfolk island": "NFK",
    "st-barthélemy": "BLM",
    "st-martin": "MAF",
    "st. pierre and miquelon": "SPM",
    "st. vin. and gren.": "VCT",
    "swaziland": "SWZ",
    "eswatini": "SWZ",
    "turks and caicos is.": "TCA",
    "u.s. virgin is.": "VIR",
    "w. sahara": "ESH",
    "wallis and futuna": "WLF",
    "america": "USA",
    "siberia": "RUS",
    "amazon": "BRA",
    "amazonia": "BRA",
    "bengal": "IND",
    "sundarbans": "IND",
    "reunion": "REU",
    "réunion": "REU",
    "sao tome": "STP",
    "sao tome and principe": "STP",
    "st pierre": "SPM",
    "guadeloupe": "GLP",
    "st barthélemy": "BLM",
    "st martin": "MAF",
    "wallis and futuna islands": "WLF",
    "wallis et futuna": "WLF",
    "kirghizstan": "KGZ",
    "kirgizia": "KGZ",
    "tadjikistan": "TJK",
    "tadzhikistan": "TJK",
    "tadzhik": "TJK",
    "aland islands": "ALA",
    "åland islands": "ALA",
    "åland": "ALA",
    "isle of man": "IMN",
    "channel islands": "GGY",
    "san marino": "SMR",
    "st lucia": "LCA",
    "st vincent": "VCT",
    "st kitts": "KNA",
    "nevis": "KNA",
    "antigua": "ATG",
    "barbuda": "ATG",
    "turks and caicos": "TCA",
    "curacao": "CUW",
    "sint maarten": "MAF",
    "falkland": "FLK",
    "falklands": "FLK",
    "heard island": "HMD",
    "heard": "HMD",
    "south georgia": "SGS",
    "sandwich islands": "SGS",
    "saipan": "MNP",
    "northern mariana": "MNP",
    "american samoa": "ASM",
    "niue": "NIU",
    "solomon": "SLB",
    "pitcairn": "PCN",
    "norfolk": "NFK",
    "yemen": "YEM",
    "east timor": "TLS",
    "timor leste": "TLS",
    "ukraine": "UKR",
    "dprk": "PRK",
    "west bank": "PSE",
    "gaza": "PSE",
    "gaza strip": "PSE",
    "malta": "MLT",
    "saint helena": "SHN",
    "tristan da cunha": "SHN",
    "faroe islands": "FRO",
    "mascarene": "MUS",
    "south dakota": "USA",
    "south florida": "USA",
    "south texas": "USA",
    "central texas": "USA",
    "central indiana": "USA",
    "west virginia": "USA",
    "chongqing": "CHN",
    "henan": "CHN",
    "hubei": "CHN",
    "hunan": "CHN",
    "jiangsu": "CHN",
    "shaanxi": "CHN",
    "shandong": "CHN",
    "tianjin": "CHN",
    "xinjiang uygur autonomous": "CHN",
    "guangxi zhuang autonomous": "CHN",
    "hebei": "CHN",
    "eastern zhejiang": "CHN",
    "northwestern china": "CHN",
    "subtropical china": "CHN",
    "nanjing": "CHN",
    "nanping city": "CHN",
    "shenmu city": "CHN",
    "shihezi": "CHN",
    "huhhot": "CHN",
    "hulun buir": "CHN",
    "hulunbuir": "CHN",
    "jiangpu": "CHN",
    "jingxi county": "CHN",
    "shanxi": "CHN",
    "xishuangbanna": "CHN",
    "east qilian mountain": "CHN",
    "sichuan provinces": "CHN",
    "central kalimantan": "IDN",
    "central sulawesi": "IDN",
    "central sumatra": "IDN",
    "south sumatra": "IDN",
    "west java": "IDN",
    "west sumatra": "IDN",
    "north sumatra": "IDN",
    "java island": "IDN",
    "timor island": "IDN",
    "north east india": "IND",
    "north india": "IND",
    "south andaman island": "IND",
    "central argentina": "ARG",
    "central germany": "DEU",
    "central mexico": "MEX",
    "north spain": "ESP",
    "west germany": "DEU",
    "west carpathian": "SVK",
    "south finland": "FIN",
    "balearic islands": "ESP",
    "gomera island": "ESP",
    "madeira island": "PRT",
    "mascarene islands": "MUS",
    "moorea island": "PYF",
    "south georgia to the leonie islands": "SGS",
    "south shetland islands": "SGS",
    "south shetlands islands": "SGS",
    "spitsbergen island": "NOR",
}

# Regions that span multiple countries. The COUNTRY_TO_ISO dict literal above silently
# drops all but the last-listed ISO for duplicate keys. This dict preserves all ISOs
# for each shared region; find_all_countries_in_text() uses it to return every country.
MULTI_COUNTRY_REGIONS: Dict[str, List[str]] = {
    "india/bangladesh":            ["IND", "BGD"],
    "southern iberian":            ["ESP", "PRT"],
    "great lakes":                 ["USA", "CAN"],
    "sonoran desert":              ["USA", "MEX"],
    "chihuahuan desert":           ["USA", "MEX"],
    "rocky mountains":             ["USA", "CAN"],
    "appalachian mountains":       ["USA", "CAN"],
    "cascade range":               ["USA", "CAN"],
    "coast ranges":                ["USA", "CAN"],
    "great plains":                ["USA", "CAN"],
    "magellanic subpolar forests": ["CHL", "ARG"],
    "valdivian temperate rain forest": ["CHL", "ARG"],
    "patagonian steppe":           ["ARG", "CHL"],
    "pampas":                      ["ARG", "URY", "BRA"],
    "gran chaco":                  ["ARG", "BOL", "PRY", "BRA"],
    "atlantic forest":             ["BRA", "ARG", "PRY"],
    "cerrado":                     ["BRA", "BOL", "PRY"],
    "yungas":                      ["BOL", "PER", "ARG"],
    "puna":                        ["ARG", "BOL", "CHL", "PER"],
    "paramo":                      ["COL", "ECU", "PER", "VEN"],
    "tumbes-chocó-magdalena":      ["COL", "ECU", "PAN", "PER"],
    "chocó-darién":                ["COL", "PAN"],
    "sino-japanese":               ["CHN", "JPN"],
    "sundanian":                   ["IDN", "MYS", "BRN"],
    "sundaland":                   ["IDN", "MYS", "BRN", "SGP", "THA"],
    "beringia":                    ["RUS", "USA"],
    "himalayas":                   ["NPL", "BTN", "IND", "CHN", "PAK"],
    "tian shan":                   ["CHN", "KAZ", "KGZ", "UZB"],
    "altai mountains":             ["RUS", "CHN", "MNG", "KAZ"],
    "sayan mountains":             ["MNG", "RUS"],
    "zagros mountains":            ["IRN", "IRQ", "TUR"],
    "iranian plateau":             ["IRN", "AFG", "PAK"],
    "armenian highlands":          ["ARM", "TUR", "IRN", "AZE", "GEO"],
    "ethiopian highlands":         ["ETH", "ERI"],
    "drakensberg":                 ["ZAF", "LSO"],
    "atlas mountains":             ["MAR", "DZA", "TUN"],
    "tibesti mountains":           ["TCD", "LBY"],
    "guinea highlands":            ["GIN", "SLE", "LBR", "CIV"],
    "cameroon highlands":          ["CMR", "NGA"],
    "new guinea highlands":        ["IDN", "PNG"],
    "new guinea":                  ["IDN", "PNG"],
}
# Patch COUNTRY_TO_ISO so each shared region maps to its primary (first-listed) country
# rather than whichever happened to be last in the dict literal.
for _region_name, _region_isos in MULTI_COUNTRY_REGIONS.items():
    COUNTRY_TO_ISO[_region_name] = _region_isos[0]

# Reverse mapping: ISO A3 code to canonical country name
ISO_TO_COUNTRY = {}
for country_name, iso_code in COUNTRY_TO_ISO.items():
    if iso_code not in ISO_TO_COUNTRY:
        ISO_TO_COUNTRY[iso_code] = country_name
    else:
        # Prefer shorter, cleaner names as canonical
        canonical = ISO_TO_COUNTRY[iso_code]
        # Skip regional modifiers
        if any(mod in country_name for mod in [" province", " region", " state", " district", " territory"]):
            continue
        # Use shorter name
        if len(country_name) < len(canonical):
            ISO_TO_COUNTRY[iso_code] = country_name

# Alias to canonical country name mapping (for normalization)
ALIAS_TO_COUNTRY = {}
for country_name, iso_code in COUNTRY_TO_ISO.items():
    canonical = ISO_TO_COUNTRY[iso_code]
    ALIAS_TO_COUNTRY[country_name] = canonical


# Continent mapping for regional analysis (iso3 -> continent)
CONTINENT_MAP = {
    'CHN': 'Asia', 'IND': 'Asia', 'JPN': 'Asia', 'IDN': 'Asia', 'PHL': 'Asia', 'THA': 'Asia', 'VNM': 'Asia', 'MYS': 'Asia', 'SGP': 'Asia', 'PAK': 'Asia',
    'BGD': 'Asia', 'MMR': 'Asia', 'LKA': 'Asia', 'NPL': 'Asia', 'BTN': 'Asia', 'AFG': 'Asia', 'KAZ': 'Asia', 'UZB': 'Asia', 'TKM': 'Asia', 'TJK': 'Asia', 'KGZ': 'Asia',
    'USA': 'North America', 'CAN': 'North America', 'MEX': 'North America',
    'BRA': 'South America', 'ARG': 'South America', 'COL': 'South America', 'PER': 'South America', 'CHL': 'South America', 'VEN': 'South America', 'ECU': 'South America', 'BOL': 'South America', 'PRY': 'South America', 'URY': 'South America', 'GUY': 'South America', 'SUR': 'South America',
    'DEU': 'Europe', 'GBR': 'Europe', 'FRA': 'Europe', 'ITA': 'Europe', 'ESP': 'Europe', 'NLD': 'Europe', 'BEL': 'Europe', 'AUT': 'Europe', 'CHE': 'Europe', 'SWE': 'Europe', 'NOR': 'Europe', 'DNK': 'Europe', 'FIN': 'Europe', 'POL': 'Europe', 'ROU': 'Europe', 'GRC': 'Europe', 'PRT': 'Europe', 'CZE': 'Europe', 'HUN': 'Europe', 'SVK': 'Europe', 'SVN': 'Europe', 'HRV': 'Europe', 'BIH': 'Europe', 'SRB': 'Europe', 'MNE': 'Europe', 'ALB': 'Europe', 'MKD': 'Europe', 'UKR': 'Europe', 'BLR': 'Europe', 'MDA': 'Europe', 'RUS': 'Europe/Asia', 'LVA': 'Europe', 'LTU': 'Europe', 'EST': 'Europe', 'ISL': 'Europe',
    'AUS': 'Oceania', 'NZL': 'Oceania', 'FJI': 'Oceania', 'PNG': 'Oceania', 'WSM': 'Oceania', 'VUT': 'Oceania', 'SLB': 'Oceania',
    'ZAF': 'Africa', 'EGY': 'Africa', 'NGA': 'Africa', 'KEN': 'Africa', 'ETH': 'Africa', 'MAR': 'Africa', 'DZA': 'Africa', 'AGO': 'Africa', 'ZWE': 'Africa', 'ZMB': 'Africa', 'MWI': 'Africa', 'MOZ': 'Africa', 'TZA': 'Africa', 'UGA': 'Africa', 'RWA': 'Africa', 'BDI': 'Africa', 'COG': 'Africa', 'COD': 'Africa', 'CMR': 'Africa', 'CAF': 'Africa', 'GAB': 'Africa', 'GNQ': 'Africa', 'GHA': 'Africa', 'CIV': 'Africa', 'BFA': 'Africa', 'MLI': 'Africa', 'SEN': 'Africa', 'TUN': 'Africa',
    'ARE': 'Middle East', 'ISR': 'Middle East', 'SAU': 'Middle East', 'IRN': 'Middle East', 'IRQ': 'Middle East', 'LBN': 'Middle East', 'SYR': 'Middle East', 'YEM': 'Middle East', 'OMN': 'Middle East', 'QAT': 'Middle East', 'BHR': 'Middle East', 'KWT': 'Middle East',
}

def get_continent(iso):
    """Map ISO3 country code to continent."""
    return CONTINENT_MAP.get(iso, 'Other')


# Tissue, guild, and biome extraction functions for multi-column field recovery
def extract_tissue_values(row, headers: List[str]) -> List[Tuple[str, str]]:
    """
    Extract tissue information from relevant columns (handles displaced values).
    Returns list of (tissue_value, source_column) tuples.
    Checks columns where tissue data might be embedded by LLM extraction.
    """
    tissue_keywords = [
        'root', 'leaf', 'stem', 'seed', 'fruit', 'flower', 'reproductive',
        'rhizosphere', 'rhizome', 'tuber', 'nodule', 'bark', 'wood', 'xylem',
        'phyllosphere', 'petiole', 'seaweed', 'foliage', 'needle', 'foliar'
    ]
    found_tissues = {}
    col_index = {name: idx for idx, name in enumerate(headers)}
    search_cols = ['tissue', 'interaction_notes', 'plant_host_raw', 'fungal_taxon_raw', 'plant_host']
    
    for col_name in search_cols:
        if col_name not in col_index:
            continue
        col_idx = col_index[col_name]
        try:
            cell_value = row[col_idx] if col_idx < len(row) else None
            if cell_value and isinstance(cell_value, str):
                text_lower = cell_value.lower()
                for keyword in tissue_keywords:
                    if keyword in text_lower and keyword not in found_tissues:
                        found_tissues[keyword] = col_name
                        break
        except (IndexError, ValueError, TypeError):
            continue
    return [(tissue, source) for tissue, source in found_tissues.items()]


def extract_guild_values(row, headers: List[str]) -> List[Tuple[str, str]]:
    """
    Extract fungal guild information from relevant columns (handles displaced values).
    Returns list of (guild_value, source_column) tuples.
    """
    guild_keywords = [
        'pgpr', 'endophyte', 'endophytic', 'biocontrol', 'pathogen', 'pathogenic',
        'mycorrhiza', 'mycorrhizal', 'antagonist', 'saprotroph', 'decomposer',
        'mutualist', 'symbiotic', 'symbiont', 'phytopathogen'
    ]
    found_guilds = {}
    col_index = {name: idx for idx, name in enumerate(headers)}
    search_cols = ['primary_guild', 'interaction_notes', 'fungal_taxon_raw', 'presence_absence_clean']
    
    for col_name in search_cols:
        if col_name not in col_index:
            continue
        col_idx = col_index[col_name]
        try:
            cell_value = row[col_idx] if col_idx < len(row) else None
            if cell_value and isinstance(cell_value, str):
                text_lower = cell_value.lower()
                for keyword in guild_keywords:
                    if keyword in text_lower and keyword not in found_guilds:
                        found_guilds[keyword] = col_name
                        break
        except (IndexError, ValueError, TypeError):
            continue
    return [(guild, source) for guild, source in found_guilds.items()]


def extract_biome_values(row, headers: List[str]) -> List[Tuple[str, str]]:
    """
    Extract biome information from relevant columns (handles displaced values).
    Returns list of (biome_value, source_column) tuples.
    """
    biome_keywords = [
        'forest', 'tropical', 'rainforest', 'woodland', 'grassland', 'prairie',
        'savanna', 'desert', 'mountain', 'alpine', 'tundra', 'wetland',
        'mangrove', 'marine', 'ocean', 'aquatic', 'estuarine', 'urban',
        'agriculture', 'field', 'orchard', 'vineyard', 'farmland', 'cerrado',
        'antarctic', 'pasture', 'salt marsh'
    ]
    found_biomes = {}
    col_index = {name: idx for idx, name in enumerate(headers)}
    search_cols = ['biome', 'interaction_notes', 'plant_host_raw', 'country']
    
    for col_name in search_cols:
        if col_name not in col_index:
            continue
        col_idx = col_index[col_name]
        try:
            cell_value = row[col_idx] if col_idx < len(row) else None
            if cell_value and isinstance(cell_value, str):
                text_lower = cell_value.lower()
                for keyword in biome_keywords:
                    if keyword in text_lower and keyword not in found_biomes:
                        found_biomes[keyword] = col_name
                        break
        except (IndexError, ValueError, TypeError):
            continue
    return [(biome, source) for biome, source in found_biomes.items()]


def find_country_in_text(text: str) -> Optional[str]:
    """
    Find country name in text using word boundaries.
    Returns the ISO A3 code if found, None otherwise.
    """
    if not text or not isinstance(text, str):
        return None
    
    text_lower = text.lower().strip()
    
    # Check for exact match first
    if text_lower in COUNTRY_TO_ISO:
        return COUNTRY_TO_ISO[text_lower]
    
    # Check for word boundary matches
    for country_name, iso_code in COUNTRY_TO_ISO.items():
        pattern = r"\b" + re.escape(country_name) + r"\b"
        if re.search(pattern, text_lower):
            return iso_code
    
    return None


def find_all_countries_in_text(text: str) -> List[str]:
    """
    Find ALL country names in text using word boundaries.
    Returns list of unique ISO A3 codes found, empty list if none.
    Prioritizes longer matches to avoid substring conflicts (e.g., 'united states' over 'united').
    Shared geographic regions (e.g. 'great plains') return all associated countries.
    """
    if not text or not isinstance(text, str):
        return []

    text_lower = text.lower().strip()
    found_countries = set()

    def _add_iso(name: str) -> None:
        if name in MULTI_COUNTRY_REGIONS:
            found_countries.update(MULTI_COUNTRY_REGIONS[name])
        elif name in COUNTRY_TO_ISO:
            found_countries.add(COUNTRY_TO_ISO[name])

    # Check for exact match first
    _add_iso(text_lower)

    # Sort by length (longest first) to match longer names first
    all_names = set(COUNTRY_TO_ISO) | set(MULTI_COUNTRY_REGIONS)
    sorted_names = sorted(all_names, key=lambda x: -len(x))

    for country_name in sorted_names:
        pattern = r"\b" + re.escape(country_name) + r"\b"
        if re.search(pattern, text_lower):
            _add_iso(country_name)

    return list(found_countries)


def consolidate_country_data(row, headers: List[str]) -> Optional[str]:
    """
    Consolidate country information across multiple data columns.
    Searches specified columns for country matches.
    Returns ISO A3 code if found, None otherwise.
    DEPRECATED: Use extract_all_countries() for comprehensive multi-country detection.
    """
    search_columns = ["country", "text", "location", "study_country", "relevant_countries"]
    
    for col in search_columns:
        if col in headers and pd.notna(row.get(col)):
            iso_code = find_country_in_text(str(row[col]))
            if iso_code:
                return iso_code
    
    return None


# Pre-sort countries by length (longest first) for better pattern matching
_COUNTRIES_BY_LENGTH = sorted(COUNTRY_TO_ISO.items(), key=lambda x: -len(x[0]))

# Pre-compile regex patterns for word boundary matching (one-time cost at module load)
_COUNTRY_PATTERNS = {}
for country_name, iso_code in COUNTRY_TO_ISO.items():
    if len(country_name) > 2:  # Skip very short names to avoid false matches
        pattern_str = r"\b" + re.escape(country_name) + r"\b"
        try:
            _COUNTRY_PATTERNS[country_name] = (re.compile(pattern_str), iso_code)
        except re.error:
            pass  # Skip patterns that fail to compile


def extract_all_countries(row, headers: List[str]) -> List[Tuple[str, str]]:
    """
    Extract ALL country information from relevant columns (fast).
    Returns list of (iso_code, source_column) tuples.
    Checks priority-ordered columns most likely to contain geographic data.
    Uses pre-compiled regex patterns for word-boundary matching (one-time cost).
    Deduplicates on ISO code - keeps first source found.
    """
    found_countries = {}  # {iso_code: source_column} - keeps first source found
    
    # Columns to check, in priority order (most likely to have geographic data first)
    search_priority = [
        'country', 'relevant_countries', 'study_country',      # Explicit country fields
        'interaction_notes',                                    # Often has location context
        'plant_host', 'plant_host_raw', 'plant_host_resolved', # Geographic host location
        'fungal_taxon', 'fungal_taxon_raw',                     # LLM sometimes includes location
        'biome',                                                # Biome can have country synonyms
    ]
    
    # Build index for fast column lookup
    col_index = {name: idx for idx, name in enumerate(headers)}
    
    # Check columns in priority order
    for col_name in search_priority:
        if col_name not in col_index:
            continue  # Column doesn't exist in this dataset
        
        col_idx = col_index[col_name]
        try:
            cell_value = row[col_idx] if col_idx < len(row) else None
            
            if cell_value and isinstance(cell_value, str) and len(cell_value.strip()) > 0:
                text_lower = cell_value.lower().strip()
                
                # Check for exact match first (fastest)
                if text_lower in COUNTRY_TO_ISO:
                    iso_code = COUNTRY_TO_ISO[text_lower]
                    if iso_code not in found_countries:
                        found_countries[iso_code] = col_name
                    continue
                
                # Check for word boundary matches using pre-compiled patterns
                # Only search if text is reasonably short (avoid ultra-long cells)
                if len(text_lower) < 5000:
                    for country_name, (pattern, iso_code) in _COUNTRY_PATTERNS.items():
                        if iso_code not in found_countries and pattern.search(text_lower):
                            found_countries[iso_code] = col_name
                            # Don't break - continue collecting all matches
        except (IndexError, ValueError, TypeError, AttributeError):
            continue
    
    return [(iso, source) for iso, source in found_countries.items()]


def get_country_name(alias: str) -> Optional[str]:
    """
    Get canonical country name for an alias.
    Returns the canonical name if found, original input otherwise.
    """
    if not alias or not isinstance(alias, str):
        return alias
    
    alias_lower = alias.lower().strip()
    return ALIAS_TO_COUNTRY.get(alias_lower, alias)


def get_iso_code(country_name: str) -> Optional[str]:
    """
    Get ISO A3 code for a country name.
    Returns ISO code if found, None otherwise.
    """
    if not country_name or not isinstance(country_name, str):
        return None
    
    return COUNTRY_TO_ISO.get(country_name.lower().strip())


def get_countries_for_iso(iso_code: str) -> List[str]:
    """
    Get all country name variants for an ISO A3 code.
    Returns list of country names, empty list if code not found.
    """
    if not iso_code or not isinstance(iso_code, str):
        return []
    
    iso_upper = iso_code.upper().strip()
    return [name for name, code in COUNTRY_TO_ISO.items() if code == iso_upper]


# Statistics about the mapping
MAPPING_STATS = {
    "total_country_variants": 973,
    "unique_country_names": 884,
    "unique_iso_codes": 240,
    "source": "Extracted from scripts/utils/country_mapping.R (tribble format)",
    "coverage": "240 unique countries/territories worldwide",
}