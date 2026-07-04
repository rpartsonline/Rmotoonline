# Shrani to kot: routes/import_customers.py
# Po uspešnem uvozu IZBRIŠI to datoteko!

from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Customer

import_bp = Blueprint('import_customers', __name__, url_prefix='/admin')

CUSTOMERS_DATA = [
  {
    "code": "4261",
    "name": "KOLEKTOR CPG D.O.O.",
    "address": "INDUSTRIJSKA CESTA 2",
    "postal": "5000 Nova Gorica",
    "phone": "05/33-84-800",
    "email": ""
  },
  {
    "code": "42653",
    "name": "STORITVE Z GRADBENO MEHANIZACIJO VALENTIN GREGORIČ S.P.",
    "address": "gregorčičeva 23a",
    "postal": "5270 Ajdovščina",
    "phone": "040 300 735",
    "email": "info@vale.si"
  },
  {
    "code": "74722",
    "name": "Kupci na blagajni  Ajdovščina",
    "address": "zupanciceva ulica 8",
    "postal": "",
    "phone": "",
    "email": "rok.jerkic@bartog.si"
  },
  {
    "code": "43373",
    "name": "PREVOZI FURLAN D.O.O.",
    "address": "MANČE 18 B",
    "postal": "5271 Vipava",
    "phone": "05 364 55 99",
    "email": "furlan.prevozi@gmail.com"
  },
  {
    "code": "39178",
    "name": "AVTOMEHANIK JERNEJ SAMEC S.P.",
    "address": "VIPAVSKA CESTA 6 E",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "jernej.samec@siol.net"
  },
  {
    "code": "34597",
    "name": "AVTOELEKTRIKA BOŽIČ D.O.O.",
    "address": "Lokavška cesta 11",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "aebozic@hotmail.com"
  },
  {
    "code": "35885",
    "name": "TRANSPORT KABAC KABIR HRVAT S.P.",
    "address": "BEVKOVA ULICA 14",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "kabir.hrvatt@gmail.com"
  },
  {
    "code": "9133",
    "name": "AVTOVLEKA IN POPRAVILA MARTIN ŠTUCIN S.P.",
    "address": "GORIŠKA CESTA 6 F",
    "postal": "5271 Vipava",
    "phone": "0599 357 36",
    "email": "stucin.racuni@gmail.com"
  },
  {
    "code": "140332",
    "name": "Juretič Sašo",
    "address": "Prvačina 132a",
    "postal": "5297 Prvačina",
    "phone": "030611757",
    "email": "saso1juretic@gmail.com"
  },
  {
    "code": "52205",
    "name": "PRIMOASFALT POLAGANJE ASFALTA D.O.O.",
    "address": "Ulica Ivana kosovela 12",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "primoasfalt@gmail.com"
  },
  {
    "code": "32033",
    "name": "AVTOSERVIS KODELJA BRANKO KODELJA S.P.",
    "address": "DUPLJE 19 A",
    "postal": "5271 Vipava",
    "phone": "040 293 866",
    "email": "info@avtoserviskodelja.si"
  },
  {
    "code": "125207",
    "name": "Pbevk, Nataša Bevk s.p.",
    "address": "Kanalski Lom 2",
    "postal": "5216 Most na Soči",
    "phone": "040615587",
    "email": "pbevk1@gmail.com;gregoric16@gmail.com"
  },
  {
    "code": "115566",
    "name": "Kupci na blagajni B2C",
    "address": "/",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "129036",
    "name": "VESELI D.O.O.",
    "address": "GORIŠKA CESTA 027B",
    "postal": "5270 Ajdovščina",
    "phone": "031 648270",
    "email": "veseli.co@siol.net"
  },
  {
    "code": "57463",
    "name": "ELITA NAGODE D.O.O.",
    "address": "ŽAPUŽE 011",
    "postal": "5270 Ajdovščina",
    "phone": "05-366-24-16",
    "email": "elita.nagode@gmail.com"
  },
  {
    "code": "14951",
    "name": "Društvo Autosport Jazon dostava: Kotnikova 9, Vrhnika",
    "address": "Stara Vrhnika 1",
    "postal": "1360 Vrhnika",
    "phone": "041 410 222",
    "email": "jazon@autosport-jazon.si"
  },
  {
    "code": "73081",
    "name": "PRODAJA REZERVNIH AVTODELOV ROK JERKIČ S.P.",
    "address": "ŽUPANČIČEVA ULICA 8",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "rok.jerkic@bartog.si"
  },
  {
    "code": "43103",
    "name": "ŠPORTNO DRUŠTVO GAS KRAS",
    "address": "OREHOVLJE 2 A",
    "postal": "5291 Miren",
    "phone": "05 3954220",
    "email": "sdgaskras@gmail.com"
  },
  {
    "code": "20700",
    "name": "Golob storitve Simon Golob s.p.",
    "address": "Goriška cesta 6",
    "postal": "5271 Vipava",
    "phone": "05-368-71-60",
    "email": "simon@golobstoritve.eu"
  },
  {
    "code": "72921",
    "name": "Balboa Rocky",
    "address": "vipavska cesta",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "fazzzo@gmail.com"
  },
  {
    "code": "91386",
    "name": "Marko Rijavec",
    "address": "kamne 16",
    "postal": "5263 Dobravlje",
    "phone": "031281897",
    "email": "rijavec.m.racing@gmail.com"
  },
  {
    "code": "40798",
    "name": "TRGO ABC d.o.o. PE Ajdovščina",
    "address": "Goriška cesta 29a",
    "postal": "5270 Ajdovščina",
    "phone": "05 364 33 05",
    "email": "leon.coha@trgoabc.si"
  },
  {
    "code": "51085",
    "name": "DELOS, TRGOVINA IN STORITVE, D.O.O.",
    "address": "KOTNIKOVA CESTA 9",
    "postal": "1360 Vrhnika",
    "phone": "",
    "email": "jan.skrjanec@prozone.si"
  },
  {
    "code": "9929",
    "name": "VULKANIZERSTVO ŠMIT, ŽIGA LIKAR S.P.",
    "address": "SLOVENSKA CESTA 41",
    "postal": "5281 Spodnja Idrija",
    "phone": "05 377 61 59",
    "email": "santorantix@gmail.com"
  },
  {
    "code": "43653",
    "name": "TOMI LAVRENČIČ S.P.",
    "address": "Vrhpolje 131",
    "postal": "5271 Vipava",
    "phone": "031 651 369",
    "email": "tomi.lavrencic@gmail.com"
  },
  {
    "code": "121055",
    "name": "Alan Daks",
    "address": "Šempeter 16",
    "postal": "",
    "phone": "051313275",
    "email": "alandaks17@gmail.com"
  },
  {
    "code": "49135",
    "name": "DEJAN PANGERC S.P.",
    "address": "Manče 21 A",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "dejanpangerc@gmail.com"
  },
  {
    "code": "1258",
    "name": "SLO",
    "address": "MIRCE 20",
    "postal": "5270 Ajdovščina",
    "phone": "041 665-324 Silvan Šelj",
    "email": "zoran@slo-car.si"
  },
  {
    "code": "20181",
    "name": "PIPISTREL D.O.O. PODJETJE ZA PROIZVODNJO ZRAČNIH PLOVIL",
    "address": "GORIŠKA CESTA 50 A",
    "postal": "5270 Ajdovščina",
    "phone": "00386 5 364 38 82",
    "email": "iztok@pipistrel.si"
  },
  {
    "code": "1330",
    "name": "PNEVMATIK SERVIS ŠTRANCAR ALEŠ S.P.",
    "address": "ULICA QUILIANO 3",
    "postal": "5270 Ajdovščina",
    "phone": "05/368 15 82",
    "email": "strancar.ales@siol.net"
  },
  {
    "code": "21899",
    "name": "PODVELB D.O.O.COL",
    "address": "COL 077A",
    "postal": "5273 Col",
    "phone": "",
    "email": "info@podvelb.si"
  },
  {
    "code": "1143",
    "name": "Vulkanizerstvo Koruza Marko Koruza s.p.",
    "address": "Župančičeva 1 A",
    "postal": "5270 Ajdovščina",
    "phone": "05 368 15 63",
    "email": "vulk.koruza@gmail.com"
  },
  {
    "code": "26107",
    "name": "AUTO",
    "address": "Selo 006",
    "postal": "5262 Črniče",
    "phone": "Tel: 05 3684740",
    "email": "rd@automex.si"
  },
  {
    "code": "100736",
    "name": "DEJAN ANTONIČ S.P.",
    "address": "Potoče 50A, Potoče",
    "postal": "5263 Dobravlje",
    "phone": "031871912",
    "email": "antonic.dejan@siol.net"
  },
  {
    "code": "92349",
    "name": "KAČIČ TRANSPORT D.O.O.",
    "address": "ŽAPUŽE 11",
    "postal": "5270 Ajdovščina",
    "phone": "040646959",
    "email": "avtoprevoznistvo.kacic@gmail.com"
  },
  {
    "code": "101649",
    "name": "Matej Kobal",
    "address": "Erzelj 24",
    "postal": "5271 Vipava",
    "phone": "040 931 367",
    "email": "matej.kobal@gmail.com"
  },
  {
    "code": "74380",
    "name": "JANKO ČEBRON s.p.",
    "address": "BATUJE 067",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "janko.cebron@gmail.com"
  },
  {
    "code": "80957",
    "name": "Verč",
    "address": "Vrtovin 131A",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "verc.borut@siol.net"
  },
  {
    "code": "7695",
    "name": "BALAVTO  D.O.O. AJDOVŠČINA",
    "address": "TOVARNIŠKA CESTA 5B",
    "postal": "5270 Ajdovščina",
    "phone": "05/365-99-00 Danijela",
    "email": "tadej.coha@balavto.si"
  },
  {
    "code": "140702",
    "name": "EUROTISK, VEZENJE IN 3D TISK, D.O.O.",
    "address": "PREDMEJA 43 A",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "nabava@eurotisk.si"
  },
  {
    "code": "30139",
    "name": "Peter Stibilj",
    "address": "Slejkoti",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "peter.stibilj@gmail.com"
  },
  {
    "code": "1987",
    "name": "Avtoservis Kobal Borut Kobal s.p.",
    "address": "Goriška cesta 74",
    "postal": "5270 Ajdovščina",
    "phone": "05/368 50 07",
    "email": "avtoservis.kobal@gmail.com"
  },
  {
    "code": "96136",
    "name": "AVTOSERVISNE STORITVE BLAŽ KOREN S.P.",
    "address": "VRHPOLJE 29",
    "postal": "5271 Vipava",
    "phone": "031576137",
    "email": "info@avtoserviskoren.si"
  },
  {
    "code": "111513",
    "name": "BA MOTORSPORT D.O.O",
    "address": "DOLENJE JEZERO 43",
    "postal": "1380 Cerknica",
    "phone": "",
    "email": "avbelj.bostjan@gmail.com"
  },
  {
    "code": "82981",
    "name": "PREVOZ BETONA IGOR HROBAT S.P.",
    "address": "SLEJKOTI 012",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "prevozbetona@siol.net"
  },
  {
    "code": "87029",
    "name": "DAVID ANDLOVIC Nosilec dopolnilne dejavnosti",
    "address": "GRADIŠČE PRI VIPAVI 039",
    "postal": "5271 Vipava",
    "phone": "040166040",
    "email": "andlovicd@gmail.com"
  },
  {
    "code": "44329",
    "name": "KOMUNALA AJDOVŠČINA D.O.O.",
    "address": "GORIŠKA CESTA 23 B",
    "postal": "5270 Ajdovščina",
    "phone": "05 3659700",
    "email": "info@ksda.si"
  },
  {
    "code": "253",
    "name": "Avto Ukmar Igor Ukmar s.p.",
    "address": "Gradiška cesta 3",
    "postal": "5271 Vipava",
    "phone": "05-368-70-10",
    "email": "info@avtoukmar.si"
  },
  {
    "code": "32000",
    "name": "STOINTAS D.O.O.",
    "address": "Goriška cesta 58",
    "postal": "5270 Ajdovščina",
    "phone": "031 615 216",
    "email": "rovscek.motocenter@gmail.com"
  },
  {
    "code": "99980",
    "name": "Luk Zjet",
    "address": "male žablje 16",
    "postal": "5270 Ajdovščina",
    "phone": "1",
    "email": "damijan.lozar79@gmail.com"
  },
  {
    "code": "55051",
    "name": "TADEJ ŠTOKELJ S.P.",
    "address": "PLANINA 098C",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "tadej.stokelj@gmail.com"
  },
  {
    "code": "74727",
    "name": "Sandi Orel",
    "address": "raša 15",
    "postal": "6222 Štanjel",
    "phone": "040480455",
    "email": "sandi.orel@gmail.com"
  },
  {
    "code": "40316",
    "name": "Simac Žable",
    "address": "Planina 98B",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "simonmihelj@gmail.com"
  },
  {
    "code": "47403",
    "name": "Rado Radovan",
    "address": "Slap",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "radovan.bukovic@gmail.com"
  },
  {
    "code": "41673",
    "name": "POB, PREVOZ OSEB IN BLAGA, D.O.O.",
    "address": "CESTA 25. JUNIJA 1 N",
    "postal": "5000 Nova Gorica",
    "phone": "05 302 2215",
    "email": "info@solapob.si"
  },
  {
    "code": "18223",
    "name": "KA3, d.o.o.",
    "address": "Vipavska cesta 6A",
    "postal": "5270 Ajdovščina",
    "phone": "05 995 49 65",
    "email": "trgovina@ka3.si;info@ka3.si"
  },
  {
    "code": "109681",
    "name": "KMK KRIS MOLEK S.P.",
    "address": "Velike Žablje 60A",
    "postal": "5263 Dobravlje",
    "phone": "040140420",
    "email": "molek.kris@gmail.com"
  },
  {
    "code": "120299",
    "name": "Mehanik Fouc",
    "address": "Stomaže 16",
    "postal": "5263 Dobravlje",
    "phone": "041517097",
    "email": "fouckar@gmail.com"
  },
  {
    "code": "80955",
    "name": "Cvjek",
    "address": "goriška 16",
    "postal": "5270 Ajdovščina",
    "phone": "041682573",
    "email": "marko.jerkic3@gmail.com"
  },
  {
    "code": "59826",
    "name": "AVTOSERVIS BOJAN PUC S.P.",
    "address": "COL 106",
    "postal": "5273 Col",
    "phone": "",
    "email": "puzz.bojan@gmail.com"
  },
  {
    "code": "128480",
    "name": "Rijavec Jaka",
    "address": "Grgar 110",
    "postal": "5270 Ajdovščina",
    "phone": "031286424",
    "email": "jaka.rijavec@gmail.com"
  },
  {
    "code": "4729",
    "name": "AGRO ROMANA D.O.O.",
    "address": "SELO 28 E",
    "postal": "5262 Črniče",
    "phone": "05 368 45 90",
    "email": "trgovina@agroromana.si"
  },
  {
    "code": "50155",
    "name": "Metod Kranjc",
    "address": "Plače 50",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "kranjc.metod357@gmail.com"
  },
  {
    "code": "118765",
    "name": "POPRAVILO DELOVNIH STROJEV KRISTIJAN ŠTRUKELJ S.P.",
    "address": "LOKAVEC 97 A",
    "postal": "5270 Ajdovščina",
    "phone": "041517378",
    "email": "kristijanstrukelj@gmail.com"
  },
  {
    "code": "50801",
    "name": "CAR",
    "address": "Vrhpolje 82A",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "kodelja.blaz@gmail.com"
  },
  {
    "code": "47312",
    "name": "Dani Konjedic",
    "address": "Ulica na lokvi 28",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "//",
    "email": "dani.konjedic@gmail.com"
  },
  {
    "code": "74381",
    "name": "AGROCURK Peter Curk s.p.",
    "address": "POTOČE 2",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "finance.agrocurk@gmail.com"
  },
  {
    "code": "15192",
    "name": "SERVIL TOMAŽ MIHELJ S.P.",
    "address": "BRJE 64",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "mihelj.tomaz@gmail.com"
  },
  {
    "code": "32601",
    "name": "PESTICO BORIS PESTELJ S.P.",
    "address": "PODRAGA 89 B",
    "postal": "5272 Podnanos",
    "phone": "(05) 366 90 39",
    "email": "pestico@hotmail.com"
  },
  {
    "code": "84613",
    "name": "Rok kravos",
    "address": "rajde",
    "postal": "5263 Dobravlje",
    "phone": "031591718",
    "email": "rok.kravos@gmail.com"
  },
  {
    "code": "81223",
    "name": "Robert Curk",
    "address": "poljana 16",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "robert.curk@gmail.com"
  },
  {
    "code": "41496",
    "name": "GOZDARSTVO IN TGM MIKLAVŽ SAJEVIC S.P.",
    "address": "VODICE 10",
    "postal": "5273 Col",
    "phone": "041 423 782",
    "email": "miklavz.sajevic.sp@gmail.com"
  },
  {
    "code": "29112",
    "name": "Štokelj Robi",
    "address": "Planina 98 b",
    "postal": "5270 Ajdovščina",
    "phone": "//",
    "email": "stokelj.robi@gmail.com"
  },
  {
    "code": "106656",
    "name": "ERIK CURK S.P.",
    "address": "Planina 5B",
    "postal": "5270 Ajdovščina",
    "phone": "040835083",
    "email": "avtoservis.curk@gmail.com"
  },
  {
    "code": "147280",
    "name": "Sulejman Cpg",
    "address": "Volčja Draga 43b",
    "postal": "5293 Volčja Draga",
    "phone": "1",
    "email": "sulejman@gmail.com"
  },
  {
    "code": "1147",
    "name": "Spider podjetje za trgovino in storitve d.o.o. Idrija",
    "address": "Vojkova ulica 16",
    "postal": "5280 Idrija",
    "phone": "05/3741-101 G. ZORAN",
    "email": "spider.doo@gmail.com"
  },
  {
    "code": "53601",
    "name": "AVTOKLEPARSTVO ŽELJKO SMOLIĆ S.P.",
    "address": "OB HUBLJU 2",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "mirza.siric@hotmail.com"
  },
  {
    "code": "75253",
    "name": "Mrevlje brt",
    "address": "Goriška 16",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "dean.mrevlje@gmail.com"
  },
  {
    "code": "73193",
    "name": "Mikuž Janko",
    "address": "colska",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "jani.mikuz@hotmail.com"
  },
  {
    "code": "87302",
    "name": "VRC D.O.O.",
    "address": "MIRCE 14",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "nabava@vrcsprings.com"
  },
  {
    "code": "51333",
    "name": "EUROTON d.o.o. PE. AJDOVŠČINA",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "117137",
    "name": "Janko šef bus",
    "address": "dobravlje 21",
    "postal": "5263 Dobravlje",
    "phone": "031361113",
    "email": "jankoslav81@gmail.com"
  },
  {
    "code": "116203",
    "name": "Transport Jan Šinigoj s.p Jan Šinigoj",
    "address": "Gojače 3/G",
    "postal": "5262 Črniče",
    "phone": "+38631859041",
    "email": "infosinigoj@gmail.com"
  },
  {
    "code": "94695",
    "name": "Mankuč",
    "address": "kolodvorska",
    "postal": "6230 Postojna",
    "phone": "",
    "email": "mankoc.martin123@gmail.com"
  },
  {
    "code": "95644",
    "name": "TRANSPORT LISJAK DARKO LISJAK S.P.",
    "address": "VOLČJI GRAD 38",
    "postal": "6223 Komen",
    "phone": "7",
    "email": "transport.lisjak@gmail.com"
  },
  {
    "code": "73194",
    "name": "Vouk Sti",
    "address": "kozina 15",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "vouk.marko@gmail.com"
  },
  {
    "code": "114519",
    "name": "KOLEKTOR MOBILITY d.o.o.",
    "address": "Vojkova ulica 10",
    "postal": "5280 Idrija",
    "phone": "+38653750718",
    "email": "Jaka.Ivancic@kolektor.com"
  },
  {
    "code": "41117",
    "name": "Miha Kete",
    "address": "Lokavec 167",
    "postal": "5270 Ajdovščina",
    "phone": "031 566 748",
    "email": "miha.kete@gmail.com"
  },
  {
    "code": "135635",
    "name": "POPRAVILA VOZIL GREGOR LOZAR S.P.",
    "address": "SELO 40 A",
    "postal": "5262 Črniče",
    "phone": "041345455",
    "email": "lozar.gregor@gmail.com"
  },
  {
    "code": "9568",
    "name": "AGRARIA KORON VOLČJA DRAGA D.O.O.",
    "address": "Volčja Draga 061B",
    "postal": "5293 Volčja Draga",
    "phone": "05/395-5007",
    "email": "ales.koron@siol.net"
  },
  {
    "code": "73753",
    "name": "PERO P",
    "address": "VIPAVA 16",
    "postal": "5271 Vipava",
    "phone": "0572891",
    "email": "pero.plesnicar@gmail.com"
  },
  {
    "code": "56029",
    "name": "TGMATIJA D.O.O.",
    "address": "SANABOR 5",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "erika.zaletel@aleph.si"
  },
  {
    "code": "106941",
    "name": "Martin Čebron",
    "address": "Preserje 4",
    "postal": "5295 Branik",
    "phone": "040 889 775",
    "email": "martin.cebron@gmail.com"
  },
  {
    "code": "16808",
    "name": "AGROKOMERC, D.O.O. DOSTAVA: Goriška cesta 5L, Vipava",
    "address": "ULICA FRANCA KRAMARJA 2",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "predračun",
    "email": "agrokomerc@outlook.com"
  },
  {
    "code": "32898",
    "name": "OZBIČ D.O.O.",
    "address": "LOME 29",
    "postal": "5274 Črni Vrh nad Idrijo",
    "phone": "",
    "email": "jozbic@gmail.com"
  },
  {
    "code": "34988",
    "name": "UNIKA TTI, TRGOVINA, TRŽENJE IGRAČ, D.O.O.",
    "address": "VOLARIČEVA ULICA 1",
    "postal": "6230 Postojna",
    "phone": "05 734 2544",
    "email": "info@unikatoy.si"
  },
  {
    "code": "15163",
    "name": "AVTOHIŠA LAVRENČIČ, BOJAN LAVRENČIČ S.P.",
    "address": "VIPAVSKA CESTA 6c",
    "postal": "5270 Ajdovščina",
    "phone": "05/36 89 334",
    "email": "bojan.lavrencic@siol.net"
  },
  {
    "code": "42326",
    "name": "RAJKO ČERMELJ S.P.",
    "address": "VRTOVIN 13B",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "cermeljrajko@gmail.com"
  },
  {
    "code": "47361",
    "name": "KAR IMPEX d.o.o. Vipava",
    "address": "GORIŠKA CESTA 3",
    "postal": "5271 Vipava",
    "phone": "05 364 0017",
    "email": "info@karimpex.si"
  },
  {
    "code": "124044",
    "name": "Adnan Haskić",
    "address": "Vrhpolje 83",
    "postal": "5271 Vipava",
    "phone": "069980123",
    "email": "ahaskic258@hotmail.com"
  },
  {
    "code": "106669",
    "name": "POTOČNIK D.O.O. PODNANOS",
    "address": "PODNANOS 079",
    "postal": "5272 Podnanos",
    "phone": "",
    "email": "info@potocnik-doo.si"
  },
  {
    "code": "64585",
    "name": "kristjan štokelj",
    "address": "Cesta 91a",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "kristjan.stokelj@gmail.com"
  },
  {
    "code": "115202",
    "name": "A1 Avto Vilijem Čermelj s.p.",
    "address": "Gojače 5 e",
    "postal": "5262 Črniče",
    "phone": "05 99 52 416",
    "email": "a1avto@siol.net"
  },
  {
    "code": "51290",
    "name": "MEGATEHNIKA D.O.O.",
    "address": "GORIŠKA CESTA 75",
    "postal": "5270 Ajdovščina",
    "phone": "059903444",
    "email": "racuni@megatehnika.si"
  },
  {
    "code": "132632",
    "name": "Safed Ajdovščina",
    "address": "ajdovščina 16 c",
    "postal": "",
    "phone": "070601609",
    "email": "safed@gmail.com"
  },
  {
    "code": "122176",
    "name": "Bajc group SRL",
    "address": "Budanje 16",
    "postal": "5271 Vipava",
    "phone": "0408862833",
    "email": "maticbajc2@gmail.com"
  },
  {
    "code": "45286",
    "name": "Mrevlje Tomi",
    "address": "Goriška cesta",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "tomimrevlje@gmail.com"
  },
  {
    "code": "86080",
    "name": "GGV D.O.O.",
    "address": "STARA VRHNIKA 66",
    "postal": "1360 Vrhnika",
    "phone": "",
    "email": "info@ggv.si"
  },
  {
    "code": "58712",
    "name": "POPRAVILO STROJEV TADEJ BOLČINA S.P.",
    "address": "KOVK 23",
    "postal": "5273 Col",
    "phone": "",
    "email": "bolcinatadej@gmail.com"
  },
  {
    "code": "781",
    "name": "Niko Volčič s.p.",
    "address": "Komen 50",
    "postal": "6223 Komen",
    "phone": "05 766 73 69",
    "email": "igor.volcic@siol.net"
  },
  {
    "code": "78514",
    "name": "Ivo Gregorič",
    "address": "zalošče 1/a",
    "postal": "5294 Dornberk",
    "phone": "040615587",
    "email": "gregoric16@gmail.com"
  },
  {
    "code": "43324",
    "name": "FUŽINAR D.O.O. TRGOVINA, STORITVE, INŽENIRING AJDOVŠČINA",
    "address": "BATUJE 83",
    "postal": "5262 Črniče",
    "phone": "053650110",
    "email": "fuzinar.batuje@siol.net"
  },
  {
    "code": "74209",
    "name": "AVTOMEHANIKA ANTON SLEJKO S.P.",
    "address": "RAVNE 10 B",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "anton.slejko@gmail.com"
  },
  {
    "code": "111125",
    "name": "TRANSPORT LISJAK DARKO LISJAK S.P.",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "17754",
    "name": "AGROSAL Trgovsko podjetje d.o.o.",
    "address": "GREGORČIČEVA ULICA 038",
    "postal": "5270 Ajdovščina",
    "phone": "05 36 89 096",
    "email": "info@agrosal.si"
  },
  {
    "code": "22076",
    "name": "Hvalič DAVID",
    "address": "Črniče 1b",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "david.hvalic@gmail.com"
  },
  {
    "code": "43182",
    "name": "INCOM d.o.o. AJDOVŠČINA",
    "address": "TOVARNIŠKA CESTA 6 A",
    "postal": "5270 Ajdovščina",
    "phone": "05 3643900",
    "email": "matjaz.vidrih@leone.si"
  },
  {
    "code": "2116",
    "name": "Kranjc Damijan s.p. Avtomehanika, avtoelektrika",
    "address": "Goriška 4",
    "postal": "5270 Ajdovščina",
    "phone": "05 36 61 432",
    "email": "mingokranjc@gmail.com"
  },
  {
    "code": "43189",
    "name": "STOJAN STIBILJ",
    "address": "USTJE 80",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "stibilj.stojan@gmail.com"
  },
  {
    "code": "43769",
    "name": "REMONA d.o.o.",
    "address": "brje 49",
    "postal": "5263 Dobravlje",
    "phone": "040507521",
    "email": "remona.transport@gmail.com"
  },
  {
    "code": "35849",
    "name": "VDM LOGAR KOVINARSTVO IN VZDRŽEVANJE D.O.O.",
    "address": "MALO POLJE 9",
    "postal": "5273 Col",
    "phone": "041 495 961",
    "email": "valter.logar@vdm-logar.si"
  },
  {
    "code": "134251",
    "name": "Furlan Bojan",
    "address": "Duplje 16",
    "postal": "5271 Vipava",
    "phone": "031369018",
    "email": "furlanbo2015@gmail.com"
  },
  {
    "code": "46940",
    "name": "AVTOPREVOZNIŠTVO IN STORITVE S TGM VLADIMIR JEKLIN S.P.",
    "address": "ŽABČE 35 A",
    "postal": "5220 Tolmin",
    "phone": "",
    "email": "vladimir.jeklin@siol.net"
  },
  {
    "code": "97680",
    "name": "Mudri Robi",
    "address": "Cankarjeva 14",
    "postal": "5000 Nova Gorica",
    "phone": "-",
    "email": "robi.mudri@gmail.com"
  },
  {
    "code": "116040",
    "name": "Inteko d.o.o.",
    "address": "Slap 3/e",
    "postal": "5271 Vipava",
    "phone": "1",
    "email": "vojko.trost@fenzy.si"
  },
  {
    "code": "99979",
    "name": "Janez Bole",
    "address": "sturje 16",
    "postal": "5270 Ajdovščina",
    "phone": "1",
    "email": "janez.bole@gmail.com"
  },
  {
    "code": "47159",
    "name": "PRIMINVEST d.o.o.",
    "address": "Potoče 2",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "rok@priminvest.si"
  },
  {
    "code": "80956",
    "name": "Bex Well",
    "address": "gradisce",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "kfz.beka23@gmail.com"
  },
  {
    "code": "93332",
    "name": "V3T TRGOVINA D.O.O.",
    "address": "GORIŠKA CESTA 4 A",
    "postal": "5271 Vipava",
    "phone": "7",
    "email": ""
  },
  {
    "code": "96254",
    "name": "Matjaž Natlačen",
    "address": "manče",
    "postal": "5271 Vipava",
    "phone": "031830457",
    "email": "matjaz.natlace@gmail.com"
  },
  {
    "code": "29270",
    "name": "GREGAGRE, PREVOZ BLAGA IN OSEB, D.O.O.",
    "address": "ŽAPUŽE 104",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "miljavec.g@gmail.com"
  },
  {
    "code": "122090",
    "name": "L.M. D.O.O.",
    "address": "KOŽMANI 22",
    "postal": "5270 Ajdovščina",
    "phone": "041831874",
    "email": "lmdooufficio@gmail.com"
  },
  {
    "code": "26354",
    "name": "GO",
    "address": "Cesta 25. junija 55, Kromberk",
    "postal": "5000 Nova Gorica",
    "phone": "",
    "email": "info@go-rent.si"
  },
  {
    "code": "23781",
    "name": "MITJA KOVAČIČ S.P.",
    "address": "ZALOŠČE 029g",
    "postal": "5294 Dornberk",
    "phone": "041-640576",
    "email": "mitja.kova@gmail.com"
  },
  {
    "code": "142668",
    "name": "TGM IN PREVOZI IVAN KOBAL S.P.",
    "address": "VIŠNJE 5 B",
    "postal": "5273 Col",
    "phone": "-",
    "email": "ivan.kobal18@gmail.com"
  },
  {
    "code": "149104",
    "name": "DLES, Dejan Premrl s.p.",
    "address": "Gradiška cesta 1",
    "postal": "5271 Vipava",
    "phone": "041456495",
    "email": "dejanpremrl@hotmail.com"
  },
  {
    "code": "58950",
    "name": "krečo matej",
    "address": "duplje 42",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "krecicm@gmail.com"
  },
  {
    "code": "47659",
    "name": "Drago Novinc",
    "address": "Lokavec",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "139306",
    "name": "GRADTECH GRADBENIŠTVO TEHNOLOGIJA D.O.O.",
    "address": "PODSKRAJNIK 45",
    "postal": "1380 Cerknica",
    "phone": "01/7097124",
    "email": "info@gradtech.si"
  },
  {
    "code": "13161",
    "name": "K",
    "address": "VELIKA POT 031",
    "postal": "5250 Solkan",
    "phone": "",
    "email": "kinvest.doo@gmail.com"
  },
  {
    "code": "81280",
    "name": "Egon Jerkič",
    "address": "medeliin 1",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "rok.jerkic@bartog.si"
  },
  {
    "code": "43160",
    "name": "ELDEFA ELEKTROINŠTALACIJE DEJAN FAKUČ S.P.",
    "address": "USTJE 37 A",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "24333786@e-racuni.com"
  },
  {
    "code": "244",
    "name": "DEBRIA d.o.o.",
    "address": "Gojače 62",
    "postal": "5262 Črniče",
    "phone": "05/3936694",
    "email": "suzana.debria@gmail.com"
  },
  {
    "code": "119314",
    "name": "DEMPER, GRADBENE STORITVE, D.O.O.",
    "address": "OTLICA 37",
    "postal": "5270 Ajdovščina",
    "phone": "041406137",
    "email": "ivan.krapez@siol.net"
  },
  {
    "code": "95211",
    "name": "MURATORI VESELI GRADBENIŠTVO D.O.O.",
    "address": "NA TRATI 2",
    "postal": "5270 Ajdovščina",
    "phone": "031705332",
    "email": "muratoriveseli@yahoo.com"
  },
  {
    "code": "43855",
    "name": "CEMAS STORITVE Z GRADBENO IN KMETIJSKO MEHANIZACIJO ALEKS SAMEC S.P.",
    "address": "MALE ŽABLJE 31 C",
    "postal": "5263 Dobravlje",
    "phone": "05 620 3232",
    "email": "aleks.samec@gmail.com"
  },
  {
    "code": "13669",
    "name": "KADUT TRGOVSKO IN STORITVENO PODJETJE D.O.O. KADUT d.o.o.",
    "address": "SELO 92",
    "postal": "5262 Črniče",
    "phone": "05 366 65 81",
    "email": "kadut.doo1@gmail.com"
  },
  {
    "code": "149421",
    "name": "KARAMELA GOSTINSKE STORITVE D.O.O.",
    "address": "UKMARJEV TRG 8",
    "postal": "6000 Koper",
    "phone": "059972121",
    "email": "info@karamela.si"
  },
  {
    "code": "125519",
    "name": "Žan Stanič",
    "address": "branik 16",
    "postal": "5295 Branik",
    "phone": "",
    "email": "bistri24@gmail.com"
  },
  {
    "code": "128775",
    "name": "STANISLAV MIKUŽ",
    "address": "ULICA GRADNIKOVE BRIGADE 019",
    "postal": "5000 Nova Gorica",
    "phone": "",
    "email": ""
  },
  {
    "code": "50188",
    "name": "AVTOPREVOZNIŠTVO IN STORITVE ŽIGA ŽLEBIR S.P.",
    "address": "BESNICA 20",
    "postal": "1000 LJUBLJANA",
    "phone": "041/431-469",
    "email": "transportizlebir@gmail.com"
  },
  {
    "code": "94243",
    "name": "GRAD",
    "address": "VRHPOLJE 101 B",
    "postal": "5271 Vipava",
    "phone": "030251401",
    "email": "grad.bau@gmail.com"
  },
  {
    "code": "108249",
    "name": "MEHANIZACIJA MILER D.O.O. PE AJDOVŠČINA",
    "address": "MIRCE 3",
    "postal": "5270 Ajdovščina",
    "phone": "041 610 303",
    "email": "rezervnideli@mehanizacija-miler.si"
  },
  {
    "code": "30886",
    "name": "AUTOMOTIVE TRGOVINA IN STORITVE PETER BRECELJ S.P.",
    "address": "MALE ŽABLJE 83",
    "postal": "5263 Dobravlje",
    "phone": "predračun, gotovina",
    "email": "peter@automotive.si"
  },
  {
    "code": "127960",
    "name": "MOŽE KROVSTVO IN KLEPARSTVO D.O.O.",
    "address": "CEBEJEVA ULICA 24",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": ""
  },
  {
    "code": "47813",
    "name": "Elektro Bratina d.o.o.",
    "address": "Gojače 80",
    "postal": "5262 Črniče",
    "phone": "041537431",
    "email": "info@elektro-bratina.si"
  },
  {
    "code": "105544",
    "name": "Mitko bmw",
    "address": "Gase 16",
    "postal": "5270 Ajdovščina",
    "phone": "041991191",
    "email": "mitja.stepancic@gmail.com"
  },
  {
    "code": "110431",
    "name": "Vouk Gregor",
    "address": "gradišče 8",
    "postal": "6243 Obrov",
    "phone": "030621244",
    "email": "vouk.gregor@gmail.com"
  },
  {
    "code": "52469",
    "name": "STORITVE S KMETIJSKO IN GOZDARSKO MEHANIZACIJO ANDRAŽ BOLČINA S.P.",
    "address": "KOVK 5 A",
    "postal": "5273 Col",
    "phone": "",
    "email": "gozd.bolcina@gmail.com"
  },
  {
    "code": "29985",
    "name": "Diagnoza in servisiranje vozil Aljaž Bratož s.p.",
    "address": "Žapuže 22",
    "postal": "5270 Ajdovščina",
    "phone": "041 950 323",
    "email": "bratoz.aljaz@gmail.com"
  },
  {
    "code": "122174",
    "name": "Kolenc Borut",
    "address": "Sežana",
    "postal": "",
    "phone": "",
    "email": "borut.kolenc@bartog.si"
  },
  {
    "code": "36928",
    "name": "BOTRAN, PREVOZNIŠTVO IN TRGOVINA, D.O.O.",
    "address": "Vipavska cesta 2c",
    "postal": "5270 Ajdovščina",
    "phone": "05 366 47 70",
    "email": "maja@batic-transport.si"
  },
  {
    "code": "147241",
    "name": "GOLDVISION, PROIZVODNJA INFORMACIJSKIH ZASLONOV, D .O.O.",
    "address": "VIPAVSKA CESTA 2 E",
    "postal": "5000 Nova Gorica",
    "phone": "1",
    "email": "janko.sef@gmail.com"
  },
  {
    "code": "74437",
    "name": "PESKANJE GM LAMETO ŽERJAL ALEN S.P.",
    "address": "KOBDILJ 6 B",
    "postal": "6222 Štanjel",
    "phone": "",
    "email": ""
  },
  {
    "code": "133919",
    "name": "Franko Zavratnik",
    "address": "Vipava 16",
    "postal": "5271 Vipava",
    "phone": "031586227",
    "email": "rjerki@gmail.com"
  },
  {
    "code": "48015",
    "name": "Metod Štrancar",
    "address": "Ulica Ivana Kosovela 23",
    "postal": "5270 Ajdovščina",
    "phone": "+38641788244",
    "email": "strancar.metod@gmail.com"
  },
  {
    "code": "43392",
    "name": "GEODRILL PODJETJE ZA RAZISKOVANJE PROIZVODNJO IN TRGOVINO D.O.O.",
    "address": "OBREŽNA ULICA 1",
    "postal": "2000 MARIBOR",
    "phone": "02 684 0086",
    "email": "stojan.geodrill@siol.net"
  },
  {
    "code": "11432",
    "name": "STOPAR PROIZVODNJA, GRADNJA, MARKETING D.O.O.",
    "address": "LOKAVEC 202 C",
    "postal": "5270 Ajdovščina",
    "phone": "05 368 9225",
    "email": "info@stopar-pgm.si"
  },
  {
    "code": "150049",
    "name": "Boštjan Batagelj",
    "address": "vrtovin 77",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "batagelj77@gmail.com"
  },
  {
    "code": "42783",
    "name": "UNIPLAN d.o.o.",
    "address": "Kostanjevica na Krasu 109",
    "postal": "5296 Kostanjevica na Krasu",
    "phone": "05 3080436",
    "email": "uniplan.prevozi@gmail.com"
  },
  {
    "code": "80887",
    "name": "FELCOM D.O.O.",
    "address": "VRHPOLJE 001D",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "felcom@siol.net"
  },
  {
    "code": "39123",
    "name": "VZDRŽEVANJE MOTORNIH VOZIL ŠTERBENK, LUKA ŠTERBENK S.P.",
    "address": "SLATINA 21 A",
    "postal": "3327 Šmartno ob Paki",
    "phone": "031 375 095",
    "email": "luka.sterbenk@gmail.com"
  },
  {
    "code": "139436",
    "name": "C.I.A.K. AUTO TRGOVINA D.O.O. PE AJDOVŠČINA",
    "address": "Mirce 14",
    "postal": "5270 Ajdovščina",
    "phone": "068/200-86-65",
    "email": "ajdovscina@ciak-auto.si"
  },
  {
    "code": "15059",
    "name": "GO",
    "address": "Na produ 10",
    "postal": "5271 Vipava",
    "phone": "05 366 5206",
    "email": "peterrehar2001@yahoo.com"
  },
  {
    "code": "17570",
    "name": "PETRIČ Proizvodnja in trgovina d.o.o.",
    "address": "GORIŠKA CESTA 057",
    "postal": "5270 Ajdovščina",
    "phone": "05/36 59 000",
    "email": "petric@petric.si"
  },
  {
    "code": "42412",
    "name": "PROCOM PLUS D.O.O",
    "address": "Tovarniška cesta 4a",
    "postal": "5270 Ajdovščina",
    "phone": "051670160",
    "email": "info@procomplus.si"
  },
  {
    "code": "65404",
    "name": "BORUT KORON",
    "address": "BRJE 073A",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "koron@siol.net"
  },
  {
    "code": "146100",
    "name": "ROBERT HONOMIHL",
    "address": "VRHPOLJE 109",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "98601",
    "name": "Igor Štor",
    "address": "Goriščka 16",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "igor.stor@gmail.com"
  },
  {
    "code": "91048",
    "name": "Velikonja Rok",
    "address": "Bevkova ulica 7",
    "postal": "5270 Ajdovščina",
    "phone": "+38651416790",
    "email": "rok.velikonja@gmail.com"
  },
  {
    "code": "28106",
    "name": "Ušaj Damijan",
    "address": "Selo 13a",
    "postal": "5262 Črniče",
    "phone": "+38640232128",
    "email": "damijan.usaj@siol.net"
  },
  {
    "code": "34775",
    "name": "TEHIMPEX PODJETJE ZA PROIZVODNJO, TRGOVINO IN INŽENIRING D.O.O.",
    "address": "GORIŠKA CESTA 17",
    "postal": "5271 Vipava",
    "phone": "02-87-05-100",
    "email": "ravne@tehimpex.si"
  },
  {
    "code": "73181",
    "name": "Stopar Codriver",
    "address": "Gradišče",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "marko.stopar4@gmail.com"
  },
  {
    "code": "8473",
    "name": "ER",
    "address": "MALA VAS PRI GROSUPLJEM 0043",
    "postal": "1290 GROSUPLJE",
    "phone": "031742808",
    "email": "info.ertac@gmail.com"
  },
  {
    "code": "146435",
    "name": "AVTO MOTO DRUŠTVO RALLY RAID TEAM VIPAVSKA DOLINA",
    "address": "TOVARNIŠKA CESTA 4 A",
    "postal": "5270 Ajdovščina",
    "phone": "1",
    "email": "jerkic.motorsport@gmail.com"
  },
  {
    "code": "98778",
    "name": "Kristjan Trošt",
    "address": "Podnanos 1 a",
    "postal": "5271 Vipava",
    "phone": "1",
    "email": "kristjan.trost@gmail.com"
  },
  {
    "code": "31116",
    "name": "HMEZAD TRGOVINA ŽALEC D.O.O.",
    "address": "ARJA VAS 103",
    "postal": "3301 Petrovče",
    "phone": "",
    "email": "matjaz.ramsak@ht.si"
  },
  {
    "code": "91385",
    "name": "Gasa Mojster",
    "address": "gasa 16",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "71402",
    "name": "POLICIJSKI SINDIKAT SLOVENIJE",
    "address": "ŠTEFANOVA ULICA 002",
    "postal": "1000 LJUBLJANA",
    "phone": "041660854",
    "email": "marko.jakac@pss-slo.org"
  },
  {
    "code": "135647",
    "name": "PROSTOVOLJNO GASILSKO DRUŠTVO PODNANOS",
    "address": "PODBREG 19",
    "postal": "5272 Podnanos",
    "phone": "",
    "email": ""
  },
  {
    "code": "92475",
    "name": "NIKO BAJC",
    "address": "GRADIŠČE 44 A",
    "postal": "5270 Ajdovščina",
    "phone": "1",
    "email": "niko.bajc@gmail.com"
  },
  {
    "code": "149545",
    "name": "LUKA ERJAVEC",
    "address": "IDRIJSKE KRNICE 3",
    "postal": "5281 Spodnja Idrija",
    "phone": "",
    "email": ""
  },
  {
    "code": "73971",
    "name": "DAVORIN MESESNEL",
    "address": "GOČE 44",
    "postal": "5271 Vipava",
    "phone": "-",
    "email": ""
  },
  {
    "code": "88884",
    "name": "Fajdiga Gašper",
    "address": "Založnikova ulica 42",
    "postal": "1351 BREZOVICA PRI LJUBLJANI",
    "phone": "+38631799456",
    "email": "fajdiga.gasper@gmail.com"
  },
  {
    "code": "33718",
    "name": "SEVER TRANSPORT D.O.O.",
    "address": "TOVARNIŠKA CESTA 6 J",
    "postal": "5270 Ajdovščina",
    "phone": "05 3681 641",
    "email": "blaz@sever-transport.si"
  },
  {
    "code": "143232",
    "name": "Gomzi  Rally",
    "address": "vipava 16a",
    "postal": "5270 Ajdovščina",
    "phone": "041698572",
    "email": "bostjan.gomizelj@gmail.com"
  },
  {
    "code": "118117",
    "name": "Mirza Numanovic CPG",
    "address": "Ajdovščina 16",
    "postal": "",
    "phone": "1",
    "email": "mirzanumanovic216@gmail.com"
  },
  {
    "code": "19270",
    "name": "SGG TOLMIN D.O.O.",
    "address": "VIPAVSKA CESTA 2 C",
    "postal": "5270 Ajdovščina",
    "phone": "05 3810700",
    "email": "info@sgg-tolmin.si; tomaz.gantar@sgg-tolmin.si"
  },
  {
    "code": "43205",
    "name": "CNC KOVŠCA d.o.o.",
    "address": "Lokavec 150",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "cnc@siol.net"
  },
  {
    "code": "62937",
    "name": "PREVOZNIŠTVO BLAŽ MIKUŽ S.P.",
    "address": "GOZD 2",
    "postal": "5273 Col",
    "phone": "",
    "email": "mikuz.blaz@gmail.com"
  },
  {
    "code": "98936",
    "name": "ALUMER STAVBNO POHIŠTVO d.o.o.",
    "address": "Malo polje 16",
    "postal": "5273 Col",
    "phone": "",
    "email": "info@alumer.si"
  },
  {
    "code": "149508",
    "name": "BIŽIĆ VALERIJA",
    "address": "NA HRIBU 23",
    "postal": "5271 Vipava",
    "phone": "+38641287102",
    "email": "valerija.bizic@gmail.com"
  },
  {
    "code": "62165",
    "name": "Kojič Alen",
    "address": "Dobravlje 91",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "77372",
    "name": "Lojze Radjator",
    "address": "prnjavor",
    "postal": "",
    "phone": "",
    "email": "matija.potrata@gmail.com"
  },
  {
    "code": "106522",
    "name": "MIRAN FABJAN S.P.",
    "address": "Budanje 3J, Budanje",
    "postal": "5271 Vipava",
    "phone": "05 3687232",
    "email": "miran.fabjan@gmail.com"
  },
  {
    "code": "148931",
    "name": "Trošt Tomaž",
    "address": "Velike Zablje 72",
    "postal": "5263 Dobravlje",
    "phone": "+38641891221",
    "email": "tomaz.trost1@gmail.com"
  },
  {
    "code": "33193",
    "name": "Aleš Prevodnik",
    "address": "Podljubelj 58a",
    "postal": "4290 Tržič",
    "phone": "051/391-893",
    "email": "ales.prevodnik@ggd.si"
  },
  {
    "code": "36436",
    "name": "CRONO d.o.o. Ajdovščina",
    "address": "VIPAVSKA CESTA 6 D",
    "postal": "5270 Ajdovščina",
    "phone": "05 366 3332",
    "email": "finance@crono.si;anej.radman@crono.si"
  },
  {
    "code": "55661",
    "name": "NABERGOJ TRANSPORT, podjetje za logistiko, d.o.o",
    "address": "Vipavska cesta 4",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "8128",
    "name": "TEHNIČNI SISTEMI,D.O.O.",
    "address": "Bizeljska cesta 85",
    "postal": "8259 Bizeljsko",
    "phone": "07/45 200 21",
    "email": "david@tesi.si"
  },
  {
    "code": "87081",
    "name": "INSTALACIJE FURLAN D.O.O.",
    "address": "SELO 076",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "instalacije.furlan@gmail.com"
  },
  {
    "code": "95352",
    "name": "PIPISTREL VERTICAL SOLUTIONS d.o.o.",
    "address": "Vipavska cesta 2, Ajdovščina,",
    "postal": "5270 Ajdovščina",
    "phone": "386 40 980 019",
    "email": "kristina.roldo@pipistrel-aircraft.com"
  },
  {
    "code": "111819",
    "name": "F.T.R. PREVOZI D.O.O.",
    "address": "V MLINU 71",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "",
    "email": "zlatko.furlan@gmail.com"
  },
  {
    "code": "147589",
    "name": "Rode Katja",
    "address": "Stara Vrhnika 32",
    "postal": "1360 Vrhnika",
    "phone": "+38640701566",
    "email": "katja.rode16@gmail.com"
  },
  {
    "code": "141410",
    "name": "ŽGUR PERUTNINARSTVO TJAŽ ŽGUR S.P.",
    "address": "POREČE 28",
    "postal": "5272 Podnanos",
    "phone": "-",
    "email": ""
  },
  {
    "code": "70869",
    "name": "ARD POSREDOVANJE ZAČASNE DELOVNE SILE, D.O.O.",
    "address": "SELO 44",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "96581",
    "name": "KOVINARSTVO TOMI RUPNIK S.P.",
    "address": "LOKAVEC 150",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "113235",
    "name": "SEBASTJAN ŠTOR S.P.",
    "address": "Cesta 65",
    "postal": "5270 Ajdovščina",
    "phone": "031 611867",
    "email": "el.stik@siol.net"
  },
  {
    "code": "56639",
    "name": "MRAK RACING NAJEM VOZIL JAN MRAK S.P.",
    "address": "MLADINSKA ULICA 5",
    "postal": "5281 Spodnja Idrija",
    "phone": "031592287",
    "email": "mrak.racing.team@gmail.com"
  },
  {
    "code": "57462",
    "name": "G A X TRGOVINA IN TRGOVINSKE STORITVE D.O.O.",
    "address": "GORIŠKA CESTA 51",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": "gaxslo@gmail.com"
  },
  {
    "code": "106341",
    "name": "MODULPLAST d.o.o.",
    "address": "Miren 137b",
    "postal": "5291 Miren",
    "phone": "1",
    "email": "info@modulplast.si"
  },
  {
    "code": "138967",
    "name": "MATIJA BIZJAK",
    "address": "PREDMEJA 95",
    "postal": "5270 Ajdovščina",
    "phone": "1",
    "email": "matija.bizjak@gmail.com"
  },
  {
    "code": "95875",
    "name": "FIRŠT Vrtovin d.o.o.",
    "address": "Vrtovin 71c",
    "postal": "5262 Črniče",
    "phone": "031249196",
    "email": "info@first-vrtovin.si"
  },
  {
    "code": "141501",
    "name": "ŽAN KOŽMAN",
    "address": "PODKRAJ 047C",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "38767",
    "name": "DUO ŽIBERNA, GRADBENO PODJETJE, D.O.O., ŠENČUR",
    "address": "SREDNJA VAS PRI ŠENČURJU 18",
    "postal": "4208 Šenčur",
    "phone": "04 2515463",
    "email": "matevz.ziberna@gmail.com"
  },
  {
    "code": "19062",
    "name": "INSTALACIJE MOHORČIČ MATJAŽ MOHORČIČ S.P.",
    "address": "USTJE 031B",
    "postal": "5270 Ajdovščina",
    "phone": "05 364 1812",
    "email": "instalacije.mohorcic@gmail.com"
  },
  {
    "code": "107056",
    "name": "AGRARIA D.O.O. TRGOVINA S KMETIJSKIM REPROMATERIAL OM DORNBERK",
    "address": "KOLODVORSKA ULICA 17 A",
    "postal": "5294 Dornberk",
    "phone": "05 3018723",
    "email": "agrariadoo@siol.net"
  },
  {
    "code": "114725",
    "name": "ŠAPLA d.o.o.",
    "address": "Lokavec 70b",
    "postal": "5270 Ajdovščina",
    "phone": "040466612",
    "email": "sapla.sandra@gmail.com"
  },
  {
    "code": "143432",
    "name": "METOD ŠTRANCAR",
    "address": "ULICA IVANA KOSOVELA 23",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "strancar.metod@gmail.com"
  },
  {
    "code": "21364",
    "name": "TUAM PREVOZI OSEB IN TURISTIČNE DEJAVNOSTI D.O.O. TURISTIČNE DEJAVNOSTI D.O.O.",
    "address": "VOJKOVA ULICA 15",
    "postal": "5270 Ajdovščina",
    "phone": "predračun!",
    "email": ""
  },
  {
    "code": "23576",
    "name": "TRANSPORT CURK D.O.O.",
    "address": "GORIŠKA CESTA 005I",
    "postal": "5271 Vipava",
    "phone": "05 366 51 86",
    "email": "info@transport-curk.si"
  },
  {
    "code": "149591",
    "name": "Kugonič Polona",
    "address": "Grivška pot 8",
    "postal": "5270 Ajdovščina",
    "phone": "+38641444317",
    "email": "polonakugonic@gmail.com"
  },
  {
    "code": "84839",
    "name": "Avto",
    "address": "IDRIJSKA CESTA 7",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": "Matej.lisjak@gmail.com"
  },
  {
    "code": "33797",
    "name": "SU",
    "address": "Vipavska cesta 2d",
    "postal": "5270 Ajdovščina",
    "phone": "040 631 064",
    "email": "info@su-sad.si"
  },
  {
    "code": "28009",
    "name": "JERNEJ CERNATIČ S.P.",
    "address": "Šempas 136",
    "postal": "5261 Šempas",
    "phone": "////",
    "email": "jernej.cernatic@gmail.com"
  },
  {
    "code": "135509",
    "name": "KOPAČIN, PREDELAVA IN PRODAJA LESA, D.O.O.",
    "address": "PODBREG 33 B",
    "postal": "5272 Podnanos",
    "phone": "031-231-583",
    "email": "kopacin@siol.net"
  },
  {
    "code": "74488",
    "name": "BEFK",
    "address": "Kamne 15a",
    "postal": "",
    "phone": "",
    "email": "befkon@gmail.com"
  },
  {
    "code": "60564",
    "name": "AVTOMEHANIKA AVTOELEKTRIKA ROBERT MEDVED S.P.",
    "address": "PARTIZANSKA ULICA 26",
    "postal": "5280 Idrija",
    "phone": "05 3722 042",
    "email": "mr.sp@siol.net"
  },
  {
    "code": "151338",
    "name": "ROBERT LIČEN",
    "address": "GOJAČE 12 A",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "75760",
    "name": "O.K.M. HOLDING D.O.O.",
    "address": "GORIŠKA CESTA 77",
    "postal": "5270 Ajdovščina",
    "phone": "05 365 9210",
    "email": "okm@okm.si"
  },
  {
    "code": "142134",
    "name": "ALAN MAJERŠIČ",
    "address": "OB HUBLJU 005",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "32447",
    "name": "MV INŽENIRING, KOVINARSTVO, MONTAŽE IN ZASTOPANJE BORUT VRČON S.P.",
    "address": "DOBRAVLJE 10 D",
    "postal": "5263 Dobravlje",
    "phone": "//",
    "email": "borut.vrcon@gmail.com"
  },
  {
    "code": "151222",
    "name": "ERIK VIDMAR",
    "address": "ŽAGOLIČ 25",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "75588",
    "name": "TIMTEC DEFENSE D.O.O. RAZVOJ IN PROIZVODNJA SISTEMOV, D.O.O.",
    "address": "GORIŠKA CESTA 6 C",
    "postal": "5271 Vipava",
    "phone": "051609651",
    "email": "procurement@timtecdefense.eu"
  },
  {
    "code": "99665",
    "name": "AVTOMEHANIKA RENATO LIČEN S.P.",
    "address": "GOJAČE 6 C",
    "postal": "5262 Črniče",
    "phone": "051 392 943",
    "email": "renato.licen@gmail.com"
  },
  {
    "code": "136599",
    "name": "GP",
    "address": "Šiška",
    "postal": "1000 LJUBLJANA",
    "phone": "-",
    "email": ""
  },
  {
    "code": "25640",
    "name": "PONTESS d.o.o.",
    "address": "Dunajska cesta 196",
    "postal": "1000 LJUBLJANA",
    "phone": "",
    "email": ""
  },
  {
    "code": "149064",
    "name": "TRGOVINA IN MONTAŽA STAVBNEGA POHIŠTVA, TRAJCHE GO CKOV S.P.",
    "address": "GRADIŠČE NAD PRVAČINO 67",
    "postal": "5292 Renče",
    "phone": "031519133",
    "email": "trajcegockov@gmail.com"
  },
  {
    "code": "151440",
    "name": "HRAST PRO D.O.O.",
    "address": "LOKAVEC 93",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "53264",
    "name": "DSD DVIGALA, MONTAŽA, SERVIS, REMONT IN PROJEKTIRANJE DVIGAL, D.O.O., LOGATEC",
    "address": "TRŽAŠKA CESTA 27 A",
    "postal": "1370 Logatec",
    "phone": "041-617-729",
    "email": "sandra@dsd-dvigala.si"
  },
  {
    "code": "87076",
    "name": "Tadeja Curk Kompara",
    "address": "LOKAVEC 46 A",
    "postal": "5270 Ajdovščina",
    "phone": "041636289",
    "email": "apartma.rebkovi@gmail.com"
  },
  {
    "code": "30773",
    "name": "Klemen Koren",
    "address": "Slap 91",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "klemen.klemen78@gmail.com"
  },
  {
    "code": "111975",
    "name": "R",
    "address": "Na hribu 41",
    "postal": "5271 Vipava",
    "phone": "4",
    "email": "info@r-glas.si"
  },
  {
    "code": "38752",
    "name": "AVTOPREVOZNIŠTVO SREČKO KOSOVEL S.P.",
    "address": "PRESERJE 14 A",
    "postal": "5295 Branik",
    "phone": "05 305 7058",
    "email": "srecko.kosovel@siol.net"
  },
  {
    "code": "74747",
    "name": "ENOOP D.O.O.",
    "address": "GORIŠKA CESTA 023",
    "postal": "5271 Vipava",
    "phone": "05 364 3470",
    "email": "info@enoop.si"
  },
  {
    "code": "121217",
    "name": "TEHNIKA AGRO D.O.O.",
    "address": "POLJE 5",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "053305805",
    "email": "info@tehnika-agro.si"
  },
  {
    "code": "24423",
    "name": "AVTOPREVOZNIŠTVO PETER CURK, S.P.",
    "address": "DOLGA POLJANA 47 B",
    "postal": "5271 Vipava",
    "phone": "041 874 511",
    "email": "curkpero@gmail.com"
  },
  {
    "code": "85983",
    "name": "BOMATIK Boris Bodiroža s.p. Boris Bodiroža",
    "address": "Bevkova 16",
    "postal": "5271 Vipava",
    "phone": "+38640799699",
    "email": "bomatik@siol.net"
  },
  {
    "code": "140260",
    "name": "CHARLIE EXPRESS JAKOMIN D.O.O.",
    "address": "DOLINSKA CESTA 1 B",
    "postal": "6000 Koper",
    "phone": "",
    "email": ""
  },
  {
    "code": "22646",
    "name": "Balboa Rok",
    "address": "Tržaška cesta",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "jerkic.motorsport@gmail.com"
  },
  {
    "code": "52715",
    "name": "KOVINARSTVO DAVID LIKAR S.P.",
    "address": "Otlica 49",
    "postal": "5270 Ajdovščina",
    "phone": "05 3649555",
    "email": "kovinarstvo.likar@siol.net"
  },
  {
    "code": "5755",
    "name": "GRADBENA MEHANIZACIJA SB  BOJAN SERAŽIN S.P.",
    "address": "VELIKO POLJE 9",
    "postal": "6210 Sežana",
    "phone": "05 769 60 30",
    "email": ""
  },
  {
    "code": "31341",
    "name": "SNICA GOSTINSTVO D.O.O.",
    "address": "LEVSTIKOVA ULICA 3",
    "postal": "5270 Ajdovščina",
    "phone": "05 3661250",
    "email": "tadejmarc@gmail.com"
  },
  {
    "code": "109485",
    "name": "GO",
    "address": "Cesta Prekomorskih brigad 62A",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "",
    "email": ""
  },
  {
    "code": "30287",
    "name": "GASILSKO REŠEVALNI CENTER AJDOVŠČINA",
    "address": "TOVARNIŠKA CESTA 3 H",
    "postal": "5270 Ajdovščina",
    "phone": "(05) 36 61 123",
    "email": "grc.ajdovscina@kabelnet.net"
  },
  {
    "code": "8711",
    "name": "SEMENIČ TRANSPORT d.o.o.",
    "address": "Podnanos 1",
    "postal": "5272 Podnanos",
    "phone": "05 364 37 10",
    "email": "tadej@semenic.eu;natasa@semenic.eu"
  },
  {
    "code": "11748",
    "name": "EUROTON d.o.o. PE. NOVA GORICA",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "99689",
    "name": "ARHITEKTURNI BIRO ŠTRANCAR MATEJ ŠTRANCAR S.P.",
    "address": "ŽUPANČIČEVA ULICA 4",
    "postal": "5270 Ajdovščina",
    "phone": "041 432 516",
    "email": "matej.strancar@gmail.com"
  },
  {
    "code": "125373",
    "name": "ZAVOD PRISTAN",
    "address": "Goriška cesta 27, Vipava, 5271 Vipava",
    "postal": "5271 Vipava",
    "phone": "05 3687750",
    "email": "info@pristan.si"
  },
  {
    "code": "9036",
    "name": "DEHKATRADE CETIN D.O.O.",
    "address": "MIRCE 22 A",
    "postal": "5270 Ajdovščina",
    "phone": "05 368  16 81",
    "email": "ozer@dehkatrade.com"
  },
  {
    "code": "17835",
    "name": "PR, ŠPORT IN TRGOVINA, D.O.O.",
    "address": "PUŠTAL 101",
    "postal": "4220 Škofja Loka",
    "phone": "",
    "email": "loka@extremevital.com"
  },
  {
    "code": "73945",
    "name": "MAZREK PLUS KOVINARSTVO D.O.O.",
    "address": "BATUJE 3 A",
    "postal": "5262 Črniče",
    "phone": "-",
    "email": "sejdi.mazrek@gmail.com"
  },
  {
    "code": "129146",
    "name": "TITANI D.O.O.",
    "address": "CESTA IV. PREKOMORSKE 10",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": ""
  },
  {
    "code": "89516",
    "name": "Nabergoj Zvonko",
    "address": "Slap 84, vipava",
    "postal": "5271 Vipava",
    "phone": "+38651655646",
    "email": "nabergojzvonko@gmail.com"
  },
  {
    "code": "33160",
    "name": "MODUL POHIŠTVENI DESIGN D.O.O.",
    "address": "PODNANOS 19",
    "postal": "5272 Podnanos",
    "phone": "",
    "email": "ales.furlan@modul-design.si"
  },
  {
    "code": "22285",
    "name": "013, PRODAJNO SERVISNI CENTER, D.O.O.",
    "address": "ARKOVA ULICA 13",
    "postal": "5280 Idrija",
    "phone": "05/37 34 040/GOTOVINA",
    "email": "rupnik.013@gmail.com"
  },
  {
    "code": "103716",
    "name": "MEMI GRADBENO IN TRGOVSKO PODJETJE D.O.O.",
    "address": "BATUJE 3 A",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "118772",
    "name": "INTBAS D.O.O.",
    "address": "MIRCE 29",
    "postal": "5270 Ajdovščina",
    "phone": "_x000D_\n040487778",
    "email": "info@intbas.com"
  },
  {
    "code": "49624",
    "name": "BLLACA d.o.o.",
    "address": "Lokavec 176",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "bllaca@gmail.com"
  },
  {
    "code": "49401",
    "name": "TU, AVTOBUSNI PREVOZI IN TURIZEM, D.O.O.",
    "address": "TRG IVANA ROBA 4",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "",
    "email": "info@kompas-ajdovscina.si"
  },
  {
    "code": "16832",
    "name": "KOBRA KLAVDIJ BRECELJ S.P.",
    "address": "POLŽEVA ULICA 025",
    "postal": "5270 Ajdovščina",
    "phone": "05/36 63 495",
    "email": "info@kobrasport.si"
  },
  {
    "code": "151426",
    "name": "Lapajne Damjan",
    "address": "Vilharjeva 28b",
    "postal": "5270 Ajdovščina",
    "phone": "+38641539715",
    "email": "damjan.lapajne@gmail.com"
  },
  {
    "code": "53006",
    "name": "AVTO ELITE D.O.O.",
    "address": "Šmihel 17",
    "postal": "5261 Šempas",
    "phone": "",
    "email": "info@avto-elite.si"
  },
  {
    "code": "5941",
    "name": "Avtoservis Aleksander Žgajnar s.p.",
    "address": "Mala vas 96",
    "postal": "5230 Bovec",
    "phone": "05/388-65-95",
    "email": "zgajnar.servis@siol.net"
  },
  {
    "code": "115900",
    "name": "DEJAN RENER",
    "address": "DOLENJE 008",
    "postal": "6222 Štanjel",
    "phone": "",
    "email": ""
  },
  {
    "code": "67150",
    "name": "TRANS KEGGLI SERVIS TOVORNIH VOZIL IN TRANSPORT, D .O.O.",
    "address": "VRTOJBENSKA CESTA 48",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "051/866-163",
    "email": "keggli.logistica@gmail.com"
  },
  {
    "code": "151301",
    "name": "OSNOVNA ŠOLA DANILA LOKARJA AJDOVŠČINA",
    "address": "CESTA 5. MAJA 15",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": ""
  },
  {
    "code": "14859",
    "name": "ČOHTRANSPORT UROŠ ČOHA S.P.",
    "address": "LOKAVEC 151 C",
    "postal": "5270 Ajdovščina",
    "phone": "031 801 980",
    "email": "coh.transport@gmail.com"
  },
  {
    "code": "15524",
    "name": "FERBA D.O.O.",
    "address": "IDRIJSKA CESTA 8",
    "postal": "5270 Ajdovščina",
    "phone": "05 368 00 88",
    "email": "ferba@siol.net"
  },
  {
    "code": "140524",
    "name": "DRIVETECH, PRODAJA REZERVNIH DELOV, ŽAK NOVAK S.P.",
    "address": "PARIŽLJE 12 C",
    "postal": "3314 Braslovče",
    "phone": "068-149-931",
    "email": "info@delinadom.si"
  },
  {
    "code": "120542",
    "name": "POPRAVILO LETAL, SVETOVANJE IN TRGOVINA MATEJ FUČK A S.P.",
    "address": "CESTA 23 C",
    "postal": "5270 Ajdovščina",
    "phone": "031370030",
    "email": "matej.1975@gmail.com"
  },
  {
    "code": "146179",
    "name": "JK",
    "address": "JAVORNIK 40",
    "postal": "178 2390 Ravne na Koroškem",
    "phone": "",
    "email": ""
  },
  {
    "code": "58020",
    "name": "AR POPRAVILA, PRODAJA IN STORITVE ANDREJ REŠETA S.P.",
    "address": "PLANINA 86",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "andrej.reseta@gmail.com"
  },
  {
    "code": "107240",
    "name": "Novak Žak",
    "address": "Parižlje 12 c",
    "postal": "3314 Braslovče",
    "phone": "+38668149931",
    "email": "novak.zak9@gmail.com"
  },
  {
    "code": "25729",
    "name": "SEKAČ IVAN ČUK S.P.",
    "address": "Črni Vrh 058",
    "postal": "5274 Črni Vrh nad Idrijo",
    "phone": "Maglica Joško",
    "email": "sekac.ivo@gmail.com"
  },
  {
    "code": "133555",
    "name": "ARTAN BYTYCI",
    "address": "TABOR 015",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "7874",
    "name": "MLINOTEST D.D",
    "address": "TOVARNIŠKA CESTA 014",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": "anja.globocnik@mlinotest.si"
  },
  {
    "code": "150969",
    "name": "ALEŠ PODOBNIK",
    "address": "COL 96",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "67674",
    "name": "ESIL POSREDNIŠTVO TRGOVINA, INSTALACIJE JAN LOZAR S.P.",
    "address": "DOBRAVLJE 5 C",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "7296",
    "name": "PREVOZI NIZKE GRAD.ERIK SEVER S.P.",
    "address": "DOBRAVLJE 49 C",
    "postal": "5263 Dobravlje",
    "phone": "05-364-60-81",
    "email": "sever.erik@gmail.com"
  },
  {
    "code": "58310",
    "name": "SILVAN FABČIČ S.P.",
    "address": "POREČE 001A",
    "postal": "5272 Podnanos",
    "phone": "05 3686131",
    "email": "silvan.fabcicsp@siol.net"
  },
  {
    "code": "89962",
    "name": "RADIVOJ LISJAK",
    "address": "ZALOŠČE 63",
    "postal": "5294 Dornberk",
    "phone": "",
    "email": "lisjak.vino@gmail.com"
  },
  {
    "code": "131796",
    "name": "DENIS LUK",
    "address": "MALE ŽABLJE 69",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "125817",
    "name": "Lemut Peter",
    "address": "Cesta 12",
    "postal": "5270 Ajdovščina",
    "phone": "0038631838137",
    "email": "lemut.peter@gmail.com"
  },
  {
    "code": "2190",
    "name": "Avtosport d.o.o. Nova Gorica",
    "address": "Sedejeva ulica 1",
    "postal": "5000 Nova Gorica",
    "phone": "",
    "email": "assport@siol.net"
  },
  {
    "code": "52192",
    "name": "Grega Žvokelj",
    "address": "Sanabor 18",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "gregorzvokelj93@gmail.com"
  },
  {
    "code": "85013",
    "name": "ZBORCI D.O.O.",
    "address": "COL 059",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "121008",
    "name": "TTL D.O.O.",
    "address": "LOKAVŠKA CESTA 7",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "60169",
    "name": "VOLK PROIZVODNJA STORITVE IN TRGOVINA D.O.O.",
    "address": "BELSKO 30",
    "postal": "6230 Postojna",
    "phone": "(05) 751 51 43",
    "email": "volkdoo@siol.net"
  },
  {
    "code": "101167",
    "name": "KAMTEHNIKA PROIZVODNJA IN STORITVE D.O.O.",
    "address": "KOLODVORSKA ULICA 1",
    "postal": "6210 Sežana",
    "phone": "",
    "email": "info@kamtehnika.si"
  },
  {
    "code": "94799",
    "name": "PETER VUK",
    "address": "Na Gmajni 18",
    "postal": "1234 Mengeš",
    "phone": "040167588",
    "email": "peter.vuk81@gmail.com"
  },
  {
    "code": "101885",
    "name": "KOVINSKA GALANTERIJA PEČNIK DARKO PEČNIK S.P.",
    "address": "GORIŠKA CESTA 53 B",
    "postal": "5270 Ajdovščina",
    "phone": "041660797",
    "email": "darko.pecnik@gmail.com"
  },
  {
    "code": "81653",
    "name": "KULINARIKA MATJAŽ COTIČ S.P.",
    "address": "ZALOŠČE 17",
    "postal": "5294 Dornberk",
    "phone": "",
    "email": ""
  },
  {
    "code": "5167",
    "name": "SINTAL  d.o.o.",
    "address": "LITOSTROJSKA CESTA 38",
    "postal": "1000 LJUBLJANA",
    "phone": "041 660 032 Dejan nabava",
    "email": "dejan.mrkun@sintal.si"
  },
  {
    "code": "150062",
    "name": "ELTEL BRANKO MRAK S.P.",
    "address": "ULICA TOMA BREJCA 016",
    "postal": "5000 Nova Gorica",
    "phone": "05 3334000",
    "email": "mrak.branko@siol.net"
  },
  {
    "code": "15550",
    "name": "KA3 , d.o.o. PE ŠEMPETER PRI NOVI GORICI",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "60026",
    "name": "ŽIČNICE JAVORNIK D.O.O.",
    "address": "LOME 28 A",
    "postal": "5274 Črni Vrh nad Idrijo",
    "phone": "05 377 7544",
    "email": "klemen.gume@gmail.com"
  },
  {
    "code": "103939",
    "name": "Tadej Grča s.p.",
    "address": "Kobjeglava 51, Kobjeglava",
    "postal": "6222 Štanjel",
    "phone": "",
    "email": "instalacije.grca@gmail.com"
  },
  {
    "code": "68695",
    "name": "ZAKLJUČNA DELA V GRADBENIŠTVU, STORITVE S TGM IN ODVOZI S TRAKTORJEM ALJAŽ REŠETA S.P.",
    "address": "PLANINA 86",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "aljaz.reseta@gmail.com"
  },
  {
    "code": "89167",
    "name": "BRANKO BAJC",
    "address": "PODKRAJ 084",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "88013",
    "name": "ZAN.I",
    "address": "Stantetova ulica 9",
    "postal": "1295 Ivančna Gorica",
    "phone": "030/711-111",
    "email": "ivancna@bartog.si"
  },
  {
    "code": "89994",
    "name": "PLESKARSTVO",
    "address": "PODKRAJ 80 A",
    "postal": "5273 Col",
    "phone": "051436160",
    "email": "damjan.kobal@gmail.com"
  },
  {
    "code": "139445",
    "name": "C.I.A.K. AUTO TRGOVINA D.O.O. PE SEŽANA",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "74199",
    "name": "KROJENJE BRUSNIH TRAKOV ZVONKO SLOKAR S.P.",
    "address": "GORIŠKA CESTA 45 A",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "32163",
    "name": "AVTOMEHANIKA POTOČNIK d.o.o.",
    "address": "ŠENTILJSKA CESTA 131 A",
    "postal": "2000 MARIBOR",
    "phone": "02 234 4040",
    "email": "servis.potocnik@telemach.net"
  },
  {
    "code": "135941",
    "name": "Nataša Purgar",
    "address": "Dombrava 11",
    "postal": "5293 Volčja Draga",
    "phone": "Bojan 031 400 409",
    "email": "natasa.purgar@hotmail.com"
  },
  {
    "code": "143076",
    "name": "Avto Jeri, Jernej Vrhovnik S.P. dostava na: Na vasi 20, Voglje, Šenčur",
    "address": "Verje 1a",
    "postal": "1215 Medvode",
    "phone": "040586579",
    "email": "avto.jeri@gmail.com"
  },
  {
    "code": "9852",
    "name": "GMT d.o.o. PE ADEL Postojna",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "26142",
    "name": "IGGITRANS PREVOZI d.o.o.",
    "address": "Pod gozdom 5",
    "postal": "1370 Logatec",
    "phone": "041 744 220",
    "email": "iggitrans@gmail.com"
  },
  {
    "code": "48358",
    "name": "AMZS d.d. PE Vipava",
    "address": "Goriška cesta 13",
    "postal": "5271 Vipava",
    "phone": "05 367 1199",
    "email": "vipava@amzs.si"
  },
  {
    "code": "151107",
    "name": "Marc Mateja",
    "address": "Ustje 78",
    "postal": "5270 Ajdovščina",
    "phone": "+38640274076",
    "email": "mateja.marc@hotmail.com"
  },
  {
    "code": "142977",
    "name": "HARI MOBIL, ODKUP IN PRODAJA VOZIL, HARIS MUŠIĆ S. P.",
    "address": "ULICA PADLIH BORCEV 7",
    "postal": "6258 PRESTRANEK",
    "phone": "",
    "email": "haris.muske@gmail.com"
  },
  {
    "code": "19098",
    "name": "BOŠTJAN LESKOVEC S.P. Dostava Vodnikova 4",
    "address": "ULICA SV. BARBARE 003",
    "postal": "5280 Idrija",
    "phone": "",
    "email": "bostjan.tulio@gmail.com"
  },
  {
    "code": "84288",
    "name": "GAPITRANS D.O.O.",
    "address": "ŠT. JURIJ 149",
    "postal": "1290 GROSUPLJE",
    "phone": "070/247-646    Igor",
    "email": "igor.matijas@gapitrans.si"
  },
  {
    "code": "26813",
    "name": "GOLD EKSPRES D.O.O.",
    "address": "PLEMLJEVA ULICA 2",
    "postal": "1210 Ljubljana - Šentvid",
    "phone": "040 55 11 33",
    "email": "matej.potocnik@lestrgovina.si"
  },
  {
    "code": "146963",
    "name": "BLAŽ PRAČEK",
    "address": "GLAVNI TRG 014",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "6942",
    "name": "PEKARNA PEČJAK D.O.O.",
    "address": "DOLENJSKA C.442 0000",
    "postal": "1291 Škofljica",
    "phone": "4",
    "email": "info@pekarna-pecjak.si"
  },
  {
    "code": "11986",
    "name": "MEHANIZACIJA MILER D.O.O.",
    "address": "DOBJA VAS 4",
    "postal": "2390 Ravne na Koroškem",
    "phone": "02 82 31 959",
    "email": "rezervnideli@mehanizacija-miler.si"
  },
  {
    "code": "127226",
    "name": "ADRiDAR Prevozi Dragan Marković s.p.",
    "address": "BEBLERJEVA ULICA 31",
    "postal": "5271 Vipava",
    "phone": "040497707",
    "email": "adridar.prevozi@gmail.com"
  },
  {
    "code": "78090",
    "name": "MONTAŽA IN SERVIS HLADILNIH NAPRAV JANEZ BERNIK S.P.",
    "address": "KLOBOVSOVA ULICA 4",
    "postal": "4220 Škofja Loka",
    "phone": "",
    "email": ""
  },
  {
    "code": "99397",
    "name": "Piščanec Julijan",
    "address": "Branik 220",
    "postal": "5295 Branik",
    "phone": "+38631494084",
    "email": "irena.piscanec@gmail.com"
  },
  {
    "code": "30126",
    "name": "TIJO, PREVOZI, D.O.O.",
    "address": "POLHOGRAJSKA CESTA 39",
    "postal": "1356 Dobrova",
    "phone": "040-163-534",
    "email": "info@tijo.si"
  },
  {
    "code": "24468",
    "name": "Zaposleni Gold Expres",
    "address": "PLEMLJEVA ULICA 2",
    "postal": "1210 Ljubljana - Šentvid",
    "phone": "///",
    "email": "andraz.stular@lestrgovina.si"
  },
  {
    "code": "33067",
    "name": "Gašper Sedej",
    "address": "Jelični Vrh 7",
    "postal": "5280 Idrija",
    "phone": "",
    "email": "gaspersedej@gmail.com"
  },
  {
    "code": "45526",
    "name": "ZIDARSTVO MATEJ BANDELJ S.P.",
    "address": "ZAVINO 18",
    "postal": "5295 Branik",
    "phone": "040 745 293",
    "email": "bandeljmatej@gmail.com"
  },
  {
    "code": "73479",
    "name": "PEGAN BRANKO  BRANKO",
    "address": "GABERJE 12",
    "postal": "6222 Štanjel",
    "phone": "051345269",
    "email": ""
  },
  {
    "code": "34199",
    "name": "CKR Chris Kobal s.p.",
    "address": "Gradišče nad prvačino 58",
    "postal": "5292 Renče",
    "phone": "//",
    "email": "ckobalrepairs@gmail.com"
  },
  {
    "code": "117079",
    "name": "GM ROVTAR D.O.O.",
    "address": "SKRILJE 24",
    "postal": "5263 Dobravlje",
    "phone": "-",
    "email": ""
  },
  {
    "code": "135646",
    "name": "ULES INTERIOR D.O.O.",
    "address": "GABERJE 25",
    "postal": "6222 Štanjel",
    "phone": "",
    "email": ""
  },
  {
    "code": "42641",
    "name": "JURIJ PREMRN",
    "address": "OREHOVICA 15",
    "postal": "5272 Podnanos",
    "phone": "",
    "email": ""
  },
  {
    "code": "47690",
    "name": "ALEKSANDER HROVATIN",
    "address": "DUPLJE 5",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "113585",
    "name": "AVTOBUSNI PREVOZI GLOBUS PREVOZNE STORITVE, D.O.O.",
    "address": "TRŽAŠKA CESTA 35",
    "postal": "6230 Postojna",
    "phone": "+",
    "email": "apglobus@hotmail.com"
  },
  {
    "code": "47332",
    "name": "TRGOVINA IN STORITVE NA DOMU JOŽICA JEŽ S.P.",
    "address": "LOŽE 53",
    "postal": "5271 Vipava",
    "phone": "05 364 5511",
    "email": "danijela.jez@gmail.com"
  },
  {
    "code": "34434",
    "name": "Seražin Gašper",
    "address": "Sela 6",
    "postal": "6210 Sežana",
    "phone": "041579530",
    "email": "gasper.serazin@gmail.com"
  },
  {
    "code": "348",
    "name": "Elsonic d.o.o.",
    "address": "Ljubljanska 43",
    "postal": "1236 Trzin",
    "phone": "041687292",
    "email": "trener.issa@gmail.com"
  },
  {
    "code": "51689",
    "name": "SIMPLI OPREMA ZA PARKE IN JAVNE POVRŠINE D.O.O.",
    "address": "SELO 11 A",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "22398",
    "name": "SERVIS VOZIL GRIL, ALJOŠA GRIL S.P.",
    "address": "ŽUPNCA 3",
    "postal": "8000 NOVO MESTO",
    "phone": "",
    "email": "aljosa.gril@gmail.com"
  },
  {
    "code": "22410",
    "name": "FILIPČIČ d.o.o.",
    "address": "PARTIZANSKA CESTA 109",
    "postal": "6210 Sežana",
    "phone": "0565444222",
    "email": "andrej@filipcic.si"
  },
  {
    "code": "30310",
    "name": "\"KO",
    "address": "GREGORČIČEVA ULICA 16",
    "postal": "5270 Ajdovščina",
    "phone": "041 590 222",
    "email": "kotnik.bojan@kobo.si"
  },
  {
    "code": "104232",
    "name": "Primož Rovtar s.p.",
    "address": "Stomaž 52",
    "postal": "5263 Dobravlje",
    "phone": "1",
    "email": "primozrovtar80@gmail.com"
  },
  {
    "code": "123583",
    "name": "MITJA TRIPKOVIĆ",
    "address": "NA LIVADI 008",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "124718",
    "name": "LAP MARKO LIPOVŽ S.P.",
    "address": "BEVKOVA ULICA 007",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "138783",
    "name": "FLUX PERFORMANCE D.O.O.",
    "address": "MIRCE 29",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "64616",
    "name": "GOZDARSTVO IN USPOSABLJANJE ROBERT ČUK S.P.",
    "address": "PODKRAJ 105 A",
    "postal": "5273 Col",
    "phone": "",
    "email": "cukroberto@gmail.com"
  },
  {
    "code": "74630",
    "name": "VRČON MARKO S.P.",
    "address": "SKRILJE 045A",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "markovrconsp@gmail.com"
  },
  {
    "code": "44443",
    "name": "ERVIN MARC",
    "address": "MALE ŽABLJE 012",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": "ervin.marc@amis.net"
  },
  {
    "code": "28081",
    "name": "Blagonja Diego",
    "address": "Žigoni 31a",
    "postal": "5292 Renče",
    "phone": "",
    "email": ""
  },
  {
    "code": "148715",
    "name": "Nemec Aleš",
    "address": "Slap 42",
    "postal": "5271 Vipava",
    "phone": "+38641819447",
    "email": "nemec.ales@gmail.com"
  },
  {
    "code": "56529",
    "name": "TOM\"S GARAGE, VZDRŽEVANJE IN POPRAVILA MOTORNIH VO",
    "address": "DOLENJSKA CESTA 145",
    "postal": "1000 LJUBLJANA",
    "phone": "",
    "email": "tomaz.krizman@gmail.com"
  },
  {
    "code": "135640",
    "name": "POLANC PROJEKTIRANJE, INŽENIRING IN SVETOVANJE D.O.O.",
    "address": "NA BRAJDI 27",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "119030",
    "name": "MATJAŽ ČUK",
    "address": "VELIKE ŽABLJE 042A",
    "postal": "5263 Dobravlje",
    "phone": "040745300",
    "email": "vinacuk.vz@gmail.com"
  },
  {
    "code": "121740",
    "name": "IRENA IPAVEC GERŽINA",
    "address": "OSEK 004B",
    "postal": "5261 Šempas",
    "phone": "",
    "email": ""
  },
  {
    "code": "51992",
    "name": "Marko Mršnik",
    "address": "Cesta na Leniec 3",
    "postal": "6210 Sežana",
    "phone": "068161511",
    "email": "markomrsnik.patriot@gmail.com"
  },
  {
    "code": "87672",
    "name": "NEJC TOMAŽIČ Nosilec dopolnilne dejavnosti na kmetiji",
    "address": "VRHPOLJE 077",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "kmetija.tomazic@siol.net"
  },
  {
    "code": "6911",
    "name": "AVTOMARK PA d.o.o.",
    "address": "Župančičeva ulica 1/d",
    "postal": "5270 Ajdovščina",
    "phone": "05-368-14-50",
    "email": "info@avtomark.com"
  },
  {
    "code": "113787",
    "name": "MIHA ŠKRLJ",
    "address": "DUPLJE 031",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "58951",
    "name": "STORITVE Z GRADBENO MEHANIZACIJO STOJAN BOŽIČ S.P.",
    "address": "KRELJEVA ULICA 10",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "36418",
    "name": "SILTONI D.O.O.",
    "address": "TOVARNIŠKA CESTA 26",
    "postal": "5270 Ajdovščina",
    "phone": "05 3658500",
    "email": "magazzino.siltoni@codognotto.com"
  },
  {
    "code": "20343",
    "name": "MARKO ŽGAVEC",
    "address": "ZADLOG 6",
    "postal": "5274 Črni Vrh nad Idrijo",
    "phone": "",
    "email": ""
  },
  {
    "code": "49573",
    "name": "Janez Valič",
    "address": "Gradišče 12",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "janezvalic@yahoo.com"
  },
  {
    "code": "148278",
    "name": "Gortnar Katja",
    "address": "Kožmani  25",
    "postal": "5270 Ajdovščina",
    "phone": "+38640620906",
    "email": "katja.gortnar@gmail.com"
  },
  {
    "code": "24469",
    "name": "UNIOIL d.o.o.",
    "address": "Partizanska cesta 109",
    "postal": "6210 Sežana",
    "phone": "05 99 65 610",
    "email": "info@unioil.si"
  },
  {
    "code": "52785",
    "name": "INSAX UROŠ SAKSIDA S.P.",
    "address": "BRANIK 156",
    "postal": "5295 Branik",
    "phone": "",
    "email": "saksida.uros@gmail.com"
  },
  {
    "code": "150685",
    "name": "Čehovin Jerica",
    "address": "gaberje 98",
    "postal": "6222 Štanjel",
    "phone": "+38641801017",
    "email": "jerica.cehovin@gmail.com"
  },
  {
    "code": "149356",
    "name": "DRAGEC KOBAL S.P.",
    "address": "GORIŠKA CESTA 27 A",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "113900",
    "name": "GRAMETI STORITVE Z GRADBENO MEHANIZACIJO IN PREVOZI MARKO TRBIŽAN S.P.",
    "address": "PLANINA 23 A",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "58587",
    "name": "DANEKS STORITVE IN TRGOVINA D.O.O. LJUBLJANA",
    "address": "POT K SEJMIŠČU 30",
    "postal": "1231 LJUBLJANA-ČRNUČE",
    "phone": "",
    "email": "darko.cecelic@gmail.com"
  },
  {
    "code": "32442",
    "name": "ŽAGA LAPAJNE, MARKO LAPAJNE S.P.",
    "address": "JELIČNI VRH 2",
    "postal": "5280 Idrija",
    "phone": "",
    "email": "lapajne.marko@siol.net"
  },
  {
    "code": "151695",
    "name": "bizjak matjaž",
    "address": "DOLGA POLJANA 2",
    "postal": "5271 Vipava",
    "phone": "+38631323217",
    "email": "matjaz_bizjak@hotmail.com"
  },
  {
    "code": "87950",
    "name": "Batic Urban",
    "address": "Cesta 56",
    "postal": "5270 Ajdovščina",
    "phone": "+38640693655",
    "email": "batic.urban@outlook.com"
  },
  {
    "code": "105689",
    "name": "AVTO UNIK D.O.O.",
    "address": "BAČ PRI MATERIJI 24",
    "postal": "6242 Materija",
    "phone": "-",
    "email": "avto.unik1@gmail.com"
  },
  {
    "code": "151453",
    "name": "PRIMOŽ ČOTAR",
    "address": "TABOR 1 A",
    "postal": "5294 Dornberk",
    "phone": "",
    "email": ""
  },
  {
    "code": "20300",
    "name": "TERČELJ AVTOPREVOZNIŠTVO IN GRADBENA MEHANIZACIJA D.O.O.",
    "address": "POLŽEVA ULICA 31",
    "postal": "5270 Ajdovščina",
    "phone": "041 518 028 Terčelj Dejan",
    "email": "tercelj.doo@gmail.com"
  },
  {
    "code": "101216",
    "name": "AVTOSERVIS KRAŠNA ROK KRAŠNA S.P.",
    "address": "Prvačina 4 A",
    "postal": "5297 Prvačina",
    "phone": "041593944",
    "email": "avtoservis.krasna@gmail.com"
  },
  {
    "code": "148767",
    "name": "Kofol Martin",
    "address": "Bilje 185C",
    "postal": "5292 Renče",
    "phone": "+38640558361",
    "email": "kofolmartin@gmail.com"
  },
  {
    "code": "28968",
    "name": "GRADBENIŠTVO MATIJA SLEJKO S.P.",
    "address": "VELIKE ŽABLJE 1",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "138420",
    "name": "Kobal Tine",
    "address": "Šempas 9",
    "postal": "5261 Šempas",
    "phone": "+38651410111",
    "email": "thetineshow@gmail.com"
  },
  {
    "code": "8103",
    "name": "GO",
    "address": "DOTI",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "140164",
    "name": "INGENIA PT D.O.O.",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "91741",
    "name": "RUDOLF Matej",
    "address": "",
    "postal": "5274 Črni Vrh nad Idrijo",
    "phone": "+38641475298",
    "email": "matejrudolf9@gmail.com"
  },
  {
    "code": "80032",
    "name": "STRUCTUM, RAZVOJ TRAJNOSTNEGA GRADBENIŠTVA, D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "80119",
    "name": "BSK Robert",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "040 804 980",
    "email": "robert.bsk@gmail.com"
  },
  {
    "code": "76557",
    "name": "Pepe Jeans",
    "address": "",
    "postal": "6230 Postojna",
    "phone": "",
    "email": "alen.cermelj@gmail.com"
  },
  {
    "code": "5139",
    "name": "DAVIDOV HRAM d.o.o.",
    "address": "",
    "postal": "3333 LJUBNO OB SAVINJI",
    "phone": "03/839-35-08",
    "email": "drago@davidovhram.si"
  },
  {
    "code": "48223",
    "name": "Trgovina Tanja Tanja Lemut Kretič s.p.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "dado.okna@siol.net"
  },
  {
    "code": "16556",
    "name": "JYSK TRGOVINA D.O.O.",
    "address": "",
    "postal": "8250 Brežice",
    "phone": "",
    "email": "pomockupcem@JYSK.com"
  },
  {
    "code": "149419",
    "name": "BLAŽ MIKUŠ",
    "address": "",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "52132",
    "name": "TANE TRANSPORT VASE ILIEVSKI S.P.",
    "address": "",
    "postal": "6230 Postojna",
    "phone": "f",
    "email": "TANETRANSPORT.SI@GMAIL.COM"
  },
  {
    "code": "112449",
    "name": "DEJAN ŠTRANCAR",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "82080",
    "name": "VELTRA D.O.O. CESTA",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "veltra@siol.net"
  },
  {
    "code": "77160",
    "name": "Robi Brajer",
    "address": "",
    "postal": "",
    "phone": "",
    "email": "robi.brajer@gmail.com"
  },
  {
    "code": "142741",
    "name": "DOMEN AMBROŽIČ",
    "address": "",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "136465",
    "name": "BENEX PLUS POSLOVNO SVETOVANJE D.O.O.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "070569800",
    "email": "kristina.marc87@gmail.com"
  },
  {
    "code": "50761",
    "name": "VODOVODNE IN CENTRALNE INŠTALACIJE MATJAŽ PETELIN S.P.",
    "address": "",
    "postal": "6223 Komen",
    "phone": "",
    "email": "matjazpetelin@gmail.com"
  },
  {
    "code": "111570",
    "name": "JAKOB BAJC s.p.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "031 804786",
    "email": "bajc.jakob@gmail.com"
  },
  {
    "code": "134443",
    "name": "FP.PRODAJA TRGOVINA IN STORITVE D.O.O.",
    "address": "",
    "postal": "8000 NOVO MESTO",
    "phone": "041 899 562- FRANCI POTOČAR",
    "email": "info@fpavto.si"
  },
  {
    "code": "72619",
    "name": "BOMATIK TRGOVINA IN STORITVE, D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "bomatik@siol.net"
  },
  {
    "code": "73608",
    "name": "INŠTITUT ZA VARNOST LOZEJ D.O.O. AJDOVŠČINA",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "info@lozej.si"
  },
  {
    "code": "91562",
    "name": "GRADPLANING POSREDNIŠTVO IN TRGOVINA, D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "114995",
    "name": "KERINBA d.o.o. Šempas",
    "address": "",
    "postal": "5261 Šempas",
    "phone": "070826655",
    "email": "jrehar@siol.net"
  },
  {
    "code": "145670",
    "name": "AE PLUS D.O.O.",
    "address": "",
    "postal": "6221 Dutovlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "67257",
    "name": "WALDORFSKA ŠOLA LJUBLJANA",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "",
    "email": ""
  },
  {
    "code": "139460",
    "name": "Boris Komel",
    "address": "",
    "postal": "5000 Nova Gorica",
    "phone": "041913644",
    "email": "boris.komel@gmail.com"
  },
  {
    "code": "143199",
    "name": "AUTOMOTION PRODAJA RABLJENIH VOZIL, D.O.O.",
    "address": "",
    "postal": "1295 Ivančna Gorica",
    "phone": "-",
    "email": "info@automotion.si"
  },
  {
    "code": "76913",
    "name": "SERVIS KOMPARA KLEMEN KOMPARA S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "7",
    "email": "kompara.s.p@gmail.com"
  },
  {
    "code": "136645",
    "name": "Strenčan Urh",
    "address": "",
    "postal": "3000 CELJE",
    "phone": "051 349 447",
    "email": "urhstrencan11@gmail.com"
  },
  {
    "code": "70404",
    "name": "Bera Ljubisa",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "070264673",
    "email": "ljubisa.bera@gmail.com"
  },
  {
    "code": "147775",
    "name": "Bavec Tomaž",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "+38641338553",
    "email": "tomaz.bavec@gmail.com"
  },
  {
    "code": "1749",
    "name": "Patriks d.o.o.",
    "address": "",
    "postal": "5212 Dobrovo v Brdih",
    "phone": "05/330-87-40 / predračun",
    "email": "patriks@siol.net"
  },
  {
    "code": "35572",
    "name": "LIBRA AUTENTICA RESTAVRIRANJE IN ARHIVIRANJE KNJIŽNEGA GRADIVA, D.",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "",
    "email": ""
  },
  {
    "code": "146285",
    "name": "Persic Andraz",
    "address": "",
    "postal": "5261 Šempas",
    "phone": "+38640607109",
    "email": "andrazko.persic@gmail.com"
  },
  {
    "code": "94399",
    "name": "Zaposljeni Policija, inšpekcije",
    "address": "",
    "postal": "6230 Postojna",
    "phone": "",
    "email": ""
  },
  {
    "code": "44849",
    "name": "ARC",
    "address": "",
    "postal": "4000 KRANJ",
    "phone": "",
    "email": "dejan.krstev@arc.si"
  },
  {
    "code": "62917",
    "name": "MTL SVETOVANJE IN STORITVE IGOR MATKO S.P.",
    "address": "",
    "postal": "6221 Dutovlje",
    "phone": "040 481 113",
    "email": "igor.matko@mtl.si"
  },
  {
    "code": "147326",
    "name": "HASAN HALKIĆ",
    "address": "",
    "postal": "01000 Ljubljana",
    "phone": "",
    "email": ""
  },
  {
    "code": "27336",
    "name": "MINITOUR d.o.o.",
    "address": "",
    "postal": "8000 NOVO MESTO",
    "phone": "041 674 264",
    "email": ""
  },
  {
    "code": "59027",
    "name": "ROK KOMPARA S.P.",
    "address": "",
    "postal": "6230 Postojna",
    "phone": "(05) 726 11 01",
    "email": "vulkanizerstvo.kompara@gmail.com"
  },
  {
    "code": "42190",
    "name": "BANDELLI MATERIALI IN TEHNOLOGIJE ZA GRADBENIŠTVO D.O.O.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "Maks Bandelli",
    "email": "maks@bandelli.si"
  },
  {
    "code": "73580",
    "name": "Sead Salkić",
    "address": "",
    "postal": "6240 KOZINA",
    "phone": "",
    "email": ""
  },
  {
    "code": "60568",
    "name": "EDVARD BATIČ",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "116541",
    "name": "PMN MATEJ NABERGOJ S.P.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "041 872930",
    "email": "pmnabergoj@gmail.com"
  },
  {
    "code": "104550",
    "name": "Matjaž štrancar",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "051661422",
    "email": "avtoservis.strancar@gmail.com"
  },
  {
    "code": "5448",
    "name": "KVIBO, DRUŽBA ZA TRGOVINO IN STORITVE, D.O.O.",
    "address": "",
    "postal": "4290 Tržič",
    "phone": "jan bertoncelj",
    "email": "jan.bertoncelj@kvibo.si"
  },
  {
    "code": "4913",
    "name": "O.K.M. d.o.o.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 3659210",
    "email": "info@okm.si"
  },
  {
    "code": "4396",
    "name": "NOMAGO D.O.O.",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "05 330 31 00",
    "email": "info@nomago.si"
  },
  {
    "code": "50999",
    "name": "FPM Tech d.o.o.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "082050825",
    "email": "info@fpm-tech.si"
  },
  {
    "code": "27844",
    "name": "VZDRŽEVANJE IN PRODAJA MATEJ PETERLE S.P.",
    "address": "",
    "postal": "8210 Trebnje",
    "phone": "-",
    "email": "matejpeterle113@gmail.com"
  },
  {
    "code": "24863",
    "name": "AVTOMOTIVE CAR PARTS BOŠTJAN MARC S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "051 353 090",
    "email": "bostjan@avtomotive.com"
  },
  {
    "code": "43425",
    "name": "A.V.B., ANDREJ BIZJAK S.P.",
    "address": "",
    "postal": "6210 Sežana",
    "phone": "",
    "email": "avtovzdrzevanje.bizjak@gmail.com"
  },
  {
    "code": "22987",
    "name": "PREVOZI SLAPAR D.O.O.",
    "address": "",
    "postal": "1234 Mengeš",
    "phone": "predračun",
    "email": "slapar.prevozi@siol.net"
  },
  {
    "code": "60550",
    "name": "AVTOMEHANIKA, IZTOK PICIGA S.P. Dostava: Ježica 2",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "040-134-665",
    "email": "iztok.piciga@gmail.com"
  },
  {
    "code": "69292",
    "name": "SE",
    "address": "",
    "postal": "5280 Idrija",
    "phone": "",
    "email": "gasper@se-tech.si"
  },
  {
    "code": "147725",
    "name": "APOTRG, D.O.O.",
    "address": "",
    "postal": "23320 Chesapeake",
    "phone": "",
    "email": ""
  },
  {
    "code": "94309",
    "name": "EUROTON D.O.O. PE IDRIJA",
    "address": "",
    "postal": "5280 Idrija",
    "phone": "",
    "email": "peidrija@euroton.si"
  },
  {
    "code": "26390",
    "name": "TOMAŽIČ MATJAŽ S.P.",
    "address": "",
    "postal": "5000 Nova Gorica",
    "phone": "05 333 00 66",
    "email": "mehanika.tomazic@siol.net"
  },
  {
    "code": "74249",
    "name": "ŽAGARSTVO SEBASTJAN NOVINEC S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "146382",
    "name": "Kotnik Marko",
    "address": "",
    "postal": "3250 ROGAŠKA SLATINA",
    "phone": "+38641964668",
    "email": "ok@markokotnik.com"
  },
  {
    "code": "17851",
    "name": "Verč Borut",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "djvercek@siol.net"
  },
  {
    "code": "19430",
    "name": "GG ČRNI VRH GOZDARSTVO GREGOR RUPNIK S.P",
    "address": "",
    "postal": "5274 Črni Vrh nad Idrijo",
    "phone": "031 602 401",
    "email": "gozdarstvo.rupnik@gmail.com"
  },
  {
    "code": "74331",
    "name": "EUROTON d.o.o. PE NOVA GORICA JUNG",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "77825",
    "name": "ZAPOSLENI FAKULTETA ZA STROJNIŠTVO UL",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "070-578-515",
    "email": "luka.sterle@fs.uni-lj.si"
  },
  {
    "code": "101313",
    "name": "BOJAN MAJDIČ",
    "address": "",
    "postal": "6250 ILIRSKA BISTRICA",
    "phone": "",
    "email": ""
  },
  {
    "code": "104021",
    "name": "DENIS KORON",
    "address": "",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "104705",
    "name": "KLEPARSTVO IN KROVSTVO ENES IBRIĆ S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": "ibricenes728@gmail.com"
  },
  {
    "code": "105058",
    "name": "ALVISS Solar d.o.o.",
    "address": "",
    "postal": "1262 Dol pri Ljubljani",
    "phone": "041/698-131",
    "email": "info@alviss.si"
  },
  {
    "code": "107167",
    "name": "C",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "058500841",
    "email": "melita.kobol-skvarc@c-astral.com"
  },
  {
    "code": "109867",
    "name": "ŠPORTNO DRUŠTVO GM ŠPORT",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "031/376-200 GORAN",
    "email": "drustvogm@gmail.com"
  },
  {
    "code": "110548",
    "name": "EVGEN STIBILJ S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "041644042",
    "email": "stibilj.s.p.@gmail.com"
  },
  {
    "code": "110658",
    "name": "ADP GROUP D.O.O.",
    "address": "",
    "postal": "6000 Koper",
    "phone": "",
    "email": "info@adp-group.si"
  },
  {
    "code": "111009",
    "name": "VE.DA.PLUS D.O.O.",
    "address": "",
    "postal": "5292 Renče",
    "phone": "",
    "email": "info@prevozi-veda.com"
  },
  {
    "code": "111182",
    "name": "ŽAN UMEK S.P.",
    "address": "",
    "postal": "6223 Komen",
    "phone": "05 766 85 55",
    "email": "zan.umek@gmail.com"
  },
  {
    "code": "111588",
    "name": "GRADBENE STORITVE SAMO FURLANI S.P.",
    "address": "",
    "postal": "6223 Komen",
    "phone": "041724895",
    "email": "antonic.dean@siol.net"
  },
  {
    "code": "112692",
    "name": "SLAĐO VASIČ",
    "address": "",
    "postal": "5293 Volčja Draga",
    "phone": "051339480",
    "email": "sladjan.vasic3@gmail.com"
  },
  {
    "code": "112871",
    "name": "GERRIT JAN FREDERIK VAN DOORN S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "+38664188835",
    "email": "gjvdoorn@hotmail.com"
  },
  {
    "code": "112919",
    "name": "TEHBO D.O.O.",
    "address": "",
    "postal": "2310 Slovenska Bistrica",
    "phone": "+38628055061",
    "email": "tajnistvo@tehbo.si"
  },
  {
    "code": "113078",
    "name": "AVTOPREVOZNIK IVO PRAČEK S.P.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "041630026",
    "email": "transport.pracek@gmail.com"
  },
  {
    "code": "11413",
    "name": "BPROM D.O.O.",
    "address": "",
    "postal": "8210 Trebnje",
    "phone": "//",
    "email": "info@bprom.eu"
  },
  {
    "code": "114489",
    "name": "Nejc Marolt",
    "address": "",
    "postal": "5295 Branik",
    "phone": "041548229",
    "email": "maroltnejc98@gmail.com"
  },
  {
    "code": "114582",
    "name": "FILMPLAST D.O.O. ALENKA ŠTOR",
    "address": "",
    "postal": "5291 Miren",
    "phone": "+38641606228",
    "email": "alenka@filmplast.si"
  },
  {
    "code": "114644",
    "name": "Trbižan d.o.o.o.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "031650136",
    "email": "trbizan.m@gmail.com"
  },
  {
    "code": "115475",
    "name": "Polanc Edvin",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "031603354",
    "email": "edvin.polanc@gmail.com"
  },
  {
    "code": "116530",
    "name": "ALEKSANDER R. MISLEJ S.P.",
    "address": "",
    "postal": "5272 Podnanos",
    "phone": "05 3680000",
    "email": "mislej.plast@siol.net"
  },
  {
    "code": "118229",
    "name": "Dakskobler Alan",
    "address": "",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "0 51 313 275",
    "email": "alandaks17@gmail.com"
  },
  {
    "code": "118363",
    "name": "PROSTOVOLJNO GASILSKO DRUŠTVO AVČE",
    "address": "",
    "postal": "5213 Kanal",
    "phone": "",
    "email": ""
  },
  {
    "code": "118737",
    "name": "LUDS D.O.O.",
    "address": "",
    "postal": "5211 Kojsko",
    "phone": "",
    "email": ""
  },
  {
    "code": "119816",
    "name": "MATZ D.O.O.",
    "address": "",
    "postal": "6221 Dutovlje",
    "phone": "-",
    "email": ""
  },
  {
    "code": "1212",
    "name": "Policijski sindikat Slovenije Območni policijski sindikat Ljubljana",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "-",
    "email": ""
  },
  {
    "code": "122086",
    "name": "ETC ADRIATIC D.O.O.",
    "address": "",
    "postal": "1240 Kamnik",
    "phone": "nn",
    "email": "info@etc-adriatic.com"
  },
  {
    "code": "122205",
    "name": "KURIRSKE STORITVE ALEŠ STARC S.P.",
    "address": "",
    "postal": "6210 Sežana",
    "phone": "-",
    "email": "ales.starc79@gmail.com"
  },
  {
    "code": "124582",
    "name": "BTF, D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "-",
    "email": "info@btf.si"
  },
  {
    "code": "126683",
    "name": "MAJA SERAŽIN ČESEN S.P.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "majacesen@gmail.com"
  },
  {
    "code": "127835",
    "name": "UKMAR LOGISTIKA, MEDNARODNA ŠPEDICIJA IN TRANSPORT , D.O.O.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "-",
    "email": "ukmartrans@gmail.com"
  },
  {
    "code": "129072",
    "name": "TOPFIBRA D.O.O.",
    "address": "",
    "postal": "6258 PRESTRANEK",
    "phone": "082055560",
    "email": ""
  },
  {
    "code": "129651",
    "name": "Karun Tina",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "+38631866673",
    "email": "tinakarun101@gmail.com"
  },
  {
    "code": "132487",
    "name": "Žvanut Simon",
    "address": "",
    "postal": "5272 Podnanos",
    "phone": "+38641218043",
    "email": "zvanut.simon@gmail.com"
  },
  {
    "code": "133262",
    "name": "IPAVEC DOMEN",
    "address": "",
    "postal": "5273 Col",
    "phone": "+38668142574",
    "email": "dodoipav@gmail.com"
  },
  {
    "code": "133491",
    "name": "NB",
    "address": "",
    "postal": "1381 Rakek",
    "phone": "",
    "email": "nejnov69@gmail.com"
  },
  {
    "code": "133855",
    "name": "S.A.T. TROŠT D.O.O. VIPAVA",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "134018",
    "name": "ALPE ADRIA ADVENTURERS D.O.O.",
    "address": "",
    "postal": "5273 Col",
    "phone": "-",
    "email": "bostjan@be-active.si"
  },
  {
    "code": "134053",
    "name": "GP KUPLEN D.O.O.",
    "address": "",
    "postal": "9220 Lendava - Lendva",
    "phone": "",
    "email": ""
  },
  {
    "code": "134109",
    "name": "Tomaž Podraga 16",
    "address": "",
    "postal": "5272 Podnanos",
    "phone": "041281076",
    "email": "tomaz.pod@gmail.com"
  },
  {
    "code": "134501",
    "name": "DDK GRADBENIŠTVO, DRAGAN BOJOVIĆ, S.P.",
    "address": "",
    "postal": "6000 Koper",
    "phone": "",
    "email": ""
  },
  {
    "code": "134542",
    "name": "MELITA STEGEL",
    "address": "",
    "postal": "6258 PRESTRANEK",
    "phone": "-",
    "email": "info@smrekarjeva-domacija.si"
  },
  {
    "code": "134601",
    "name": "SIMON KUKOVEC",
    "address": "",
    "postal": "6223 Komen",
    "phone": "",
    "email": ""
  },
  {
    "code": "134728",
    "name": "ALVEDIN MEDIĆ",
    "address": "",
    "postal": ". .",
    "phone": "",
    "email": ""
  },
  {
    "code": "134841",
    "name": "TOMAŽ VINAZZA",
    "address": "",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "",
    "email": ""
  },
  {
    "code": "135080",
    "name": "POLAGANJE TALNIH OBLOG IN PLOŠČ ANJA GORJAN S.P.",
    "address": "",
    "postal": "5292 Renče",
    "phone": "",
    "email": ""
  },
  {
    "code": "13589",
    "name": "ARTCOM EPT D.O.O.",
    "address": "",
    "postal": "6000 Koper",
    "phone": "041 664 956",
    "email": ""
  },
  {
    "code": "136109",
    "name": "Čehovin Nejc",
    "address": "",
    "postal": "6222 Štanjel",
    "phone": "+38640581943",
    "email": ""
  },
  {
    "code": "136258",
    "name": "Metodija Vangelovski",
    "address": "",
    "postal": "5281 Spodnja Idrija",
    "phone": "070 488 914",
    "email": "metodija1998@gmail.com"
  },
  {
    "code": "137143",
    "name": "EKOLINE D.O.O.",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "137194",
    "name": "BUREAU VERITAS, D.O.O.",
    "address": "",
    "postal": "01000 Ljubljana",
    "phone": "",
    "email": ""
  },
  {
    "code": "137297",
    "name": "ČRT PLAHUTA",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "137340",
    "name": "BITORIOUS D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "137473",
    "name": "JAN PREGELJ",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "137979",
    "name": "Štrancar Matjaž",
    "address": "",
    "postal": "",
    "phone": "040295033",
    "email": "m4tjaz.strancar@gmail.com"
  },
  {
    "code": "138119",
    "name": "Tominec Neli",
    "address": "",
    "postal": "5294 Dornberk",
    "phone": "+38640217680",
    "email": "nelisamec@hotmail.com"
  },
  {
    "code": "138130",
    "name": "MIHA KOŽELJ",
    "address": "",
    "postal": "01000 Ljubljana",
    "phone": "",
    "email": ""
  },
  {
    "code": "138164",
    "name": "LEDUS, ZASTOPNIŠTVO IN MONTAŽA, D.O.O.",
    "address": "",
    "postal": "5297 Prvačina",
    "phone": "040 206 765",
    "email": "david@ledus.si"
  },
  {
    "code": "138755",
    "name": "DAMJAN ŽENKO",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "138803",
    "name": "MARKO PREGELJ",
    "address": "",
    "postal": "5273 Col",
    "phone": "",
    "email": ""
  },
  {
    "code": "138923",
    "name": "Zdešar Maja",
    "address": "",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "",
    "email": ""
  },
  {
    "code": "138932",
    "name": "NERMIN DUBRAVAC",
    "address": "",
    "postal": "8000 NOVO MESTO",
    "phone": "",
    "email": ""
  },
  {
    "code": "138969",
    "name": "MAAN STROJNE INSTALACIJE MARKO PREGELJ S.P.",
    "address": "",
    "postal": "5273 Col",
    "phone": "1",
    "email": "marko.pregelj@gmail.com"
  },
  {
    "code": "138989",
    "name": "Likar Primož",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "+38641743412",
    "email": "primozlikar8@gmail.com"
  },
  {
    "code": "139009",
    "name": "Beltram Erik",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "+38640353336",
    "email": "erik.beltram33@gmail.com"
  },
  {
    "code": "139141",
    "name": "Praček Metod",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "+38631592333",
    "email": "metod.pracek@gmail.com"
  },
  {
    "code": "139619",
    "name": "MATEJ TOMAŽIČ",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "15764",
    "name": "DE",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "17674",
    "name": "VELO D.O.O.  PE AVTOHIŠA",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05/366 31 77",
    "email": "velo.ajdovscina@velo.si"
  },
  {
    "code": "17912",
    "name": "IVAN ŠINIGOJ",
    "address": "",
    "postal": "5294 Dornberk",
    "phone": "05134 6134",
    "email": "kmetija.baloh@gmail.com"
  },
  {
    "code": "19222",
    "name": "IKSPORT, trgovina, poslovne in športne dejavnosti in storitve, d.o.o.",
    "address": "",
    "postal": "5280 Idrija",
    "phone": "1",
    "email": "info@iksport.si"
  },
  {
    "code": "19340",
    "name": "Frenky",
    "address": "",
    "postal": "5282 Cerkno",
    "phone": "",
    "email": "Franci.bozic@gmail.com"
  },
  {
    "code": "19378",
    "name": "A.B.C. AVTO CENTER D.O.O.",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "20597",
    "name": "KAMIOLAND d.o.o.",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "08 205 37 55 Beni Metelko",
    "email": "info@kamioland.si;iztok@kamioland.si"
  },
  {
    "code": "21321",
    "name": "Rabatni pogoji za B2C in Supergumo",
    "address": "",
    "postal": "8210 Trebnje",
    "phone": "",
    "email": ""
  },
  {
    "code": "22613",
    "name": "LAMPE STORITVE Z GRADBENO MEHANIZACIJO PETER LAMPE S.P.",
    "address": "",
    "postal": "5273 Col",
    "phone": "4",
    "email": "peter@lampe.si"
  },
  {
    "code": "26810",
    "name": "Potokar d.o.o. PE AJDOVŠČINA",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 366 34 94",
    "email": "ajdovscina@potokar.si"
  },
  {
    "code": "28132",
    "name": "Mustafa Lozic",
    "address": "",
    "postal": "5280 Idrija",
    "phone": "//",
    "email": ""
  },
  {
    "code": "292",
    "name": "Potokar d.o.o. Ljubljana",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "30943",
    "name": "AVTOSERVIS KOMEL BLAŽ KOMEL S.P.",
    "address": "",
    "postal": "5000 Nova Gorica",
    "phone": "//",
    "email": "blaz.komel@gmail.com"
  },
  {
    "code": "31208",
    "name": "POPRAVILO STROJNE MEHANIZACIJE ELVIS VIDMAR S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "031217040",
    "email": "vidmarelvis@gmail.com"
  },
  {
    "code": "31392",
    "name": "Aleš Furlan",
    "address": "",
    "postal": "5272 Podnanos",
    "phone": "+38641506442",
    "email": "ales.furlan@modul-design.si"
  },
  {
    "code": "32161",
    "name": "AVTOBIZJAK LIČARSTVO, KLEPARSTVO JURIJ BIZJAK S.P.",
    "address": "",
    "postal": "5275 Godovič",
    "phone": "",
    "email": "jurbiz007@gmail.com"
  },
  {
    "code": "32423",
    "name": "KMETIJSKA ZADRUGA VIPAVA Z.O.O.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "05 36 47 400",
    "email": "trg1@kzvipava.si;stanka@kzvipava.si"
  },
  {
    "code": "3249",
    "name": "GMT d.o.o. P.E. Adel LJ",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "33309",
    "name": "SAMIR DŽAFEROVIĆ S.P.",
    "address": "",
    "postal": "4220 Škofja Loka",
    "phone": "///",
    "email": "acloka.sd@gmail.com"
  },
  {
    "code": "35038",
    "name": "ROMAN ZELINŠČEK",
    "address": "",
    "postal": "5250 Solkan",
    "phone": "",
    "email": ""
  },
  {
    "code": "35918",
    "name": "R.TRIS STORITVENA DEJAVNOST IN TRGOVINA, D.O.O., R IBNICA",
    "address": "",
    "postal": "1310 Ribnica",
    "phone": "",
    "email": ""
  },
  {
    "code": "35941",
    "name": "AVTOVLEKA IN POPRAVILA JAN KOREN S.P.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "nn",
    "email": "avtovleka.jankoren@gmail.com"
  },
  {
    "code": "36260",
    "name": "S.T.O.R.K. LOGISTIČNE STORITVE, DIMITRIJ MARGON, S.P.",
    "address": "",
    "postal": "4270 Jesenice",
    "phone": "040 121 408",
    "email": "info@stork-transport.si"
  },
  {
    "code": "36566",
    "name": "B. MAKOVEC TRANSPORT D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05/366-40-10",
    "email": "info@transmakovec.si"
  },
  {
    "code": "37079",
    "name": "KIPGO PROIZVODNJA, TRGOVINA, STORITVE, D.O.O.",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "kipgob@gmail.com"
  },
  {
    "code": "38587",
    "name": "GOZDARSTVO GOZD JACK IVAN MIKUŠ S.P.",
    "address": "",
    "postal": "5273 Col",
    "phone": "041/312-807",
    "email": "jack@gmail.com"
  },
  {
    "code": "39120",
    "name": "Nabergoj Kristjan",
    "address": "",
    "postal": "6240 KOZINA",
    "phone": "051 306 865",
    "email": "kristjan.nabergoj@gmail.com"
  },
  {
    "code": "39445",
    "name": "AKTUAL INT TRGOVINA POSREDNIŠTVO PREVOZI D.O.O.",
    "address": "",
    "postal": "1291 Škofljica",
    "phone": "070-344-400",
    "email": "aktualint@gmail.com"
  },
  {
    "code": "39452",
    "name": "Bartog d.o.o. Trebnje MP Ajdovščina",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "39725",
    "name": "Furlan Roža",
    "address": "",
    "postal": "5295 Branik",
    "phone": "",
    "email": ""
  },
  {
    "code": "40323",
    "name": "STRNAD JACQUES",
    "address": "",
    "postal": "6210 Sežana",
    "phone": "//",
    "email": "jacques.strnad@gmail.com"
  },
  {
    "code": "40530",
    "name": "KOKOLARI GRADBENIŠTVO D.O.O.",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "41489",
    "name": "PEČELIN d.o.o.",
    "address": "",
    "postal": "4226 Žiri",
    "phone": "04 51 06 400",
    "email": "bus.pecelin@siol.net"
  },
  {
    "code": "41576",
    "name": "CHROMING, d.o.o.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "blanka.jelen@chroming.si"
  },
  {
    "code": "42050",
    "name": "R Pisarna ajdovščina",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "rok.jerkic@bartog.si"
  },
  {
    "code": "42141",
    "name": "LOGMAS TRANSPORT D.O.O.",
    "address": "",
    "postal": "5290 ŠEMPETER PRI GORICI",
    "phone": "05-30-80-725",
    "email": "MARUSIC.TRANSPORT@GMAIL.COM"
  },
  {
    "code": "42597",
    "name": "DARE d.o.o.",
    "address": "",
    "postal": "5272 Podnanos",
    "phone": "",
    "email": "dare.storitve@gmail.com"
  },
  {
    "code": "43531",
    "name": "Marjan Čuk",
    "address": "",
    "postal": "6222 Štanjel",
    "phone": "",
    "email": ""
  },
  {
    "code": "43731",
    "name": "David Slejko dopolnilna dejavnost",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "44719",
    "name": "BRST PREDELAVA IN PRODAJA LESA D.O.O.",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": "brst.les@siol.net"
  },
  {
    "code": "45285",
    "name": "AVTOVLEKA SUNČK KLEMEN KOREN S.P.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "031857070",
    "email": "klemen.klemen78@gmail.com"
  },
  {
    "code": "45488",
    "name": "MARIJAN KOREN S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "makoren@gmail.com"
  },
  {
    "code": "46280",
    "name": "MEHANIKA VL VLADIMIR LISJAK S.P.",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "47456",
    "name": "Petejan Simon Avtoprevozništvo Petejan Simon s.p.",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "47513",
    "name": "MAR",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 368 15 82",
    "email": ""
  },
  {
    "code": "47944",
    "name": "Mrki Čajić",
    "address": "",
    "postal": "5000 Nova Gorica",
    "phone": "",
    "email": ""
  },
  {
    "code": "48012",
    "name": "STEKLARSTVO LOVERČIČ d.o.o.",
    "address": "",
    "postal": "5262 Črniče",
    "phone": "",
    "email": ""
  },
  {
    "code": "48186",
    "name": "FRUCTAL d.o.o.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 3691000",
    "email": "info@fructal.si"
  },
  {
    "code": "48918",
    "name": "GMT d.o.o. PE Ljutomer",
    "address": "",
    "postal": "",
    "phone": "",
    "email": ""
  },
  {
    "code": "50667",
    "name": "AVTOPREVOZNIŠTVO MATIČIČ TONE MATIČIČ S.P.",
    "address": "",
    "postal": "6232 Planina",
    "phone": "",
    "email": ""
  },
  {
    "code": "50767",
    "name": "GRAMIK GRADBENO IN TRGOVSKO PODJETJE D.O.O. OTLICA",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 3649525",
    "email": "miran.krapez@gmail.com"
  },
  {
    "code": "51447",
    "name": "David Rustja",
    "address": "",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "53538",
    "name": "\"PREVOZNIK\", DARKO JAKLIČ S.P.",
    "address": "",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "55299",
    "name": "VILAVI, NEPREMIČNINE IN INŽENIRING, D.O.O.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": "info@vilavi.si"
  },
  {
    "code": "57038",
    "name": "POLAGANJE OBLOG IN ZASTOPANJE, BOGDAN PAVLIN, S.P.",
    "address": "",
    "postal": "5272 Podnanos",
    "phone": "",
    "email": ""
  },
  {
    "code": "59940",
    "name": "SKAPIN ELEKTROTEHNIČNO PODJETJE D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 3644162",
    "email": "info@skapin.si"
  },
  {
    "code": "60915",
    "name": "RAJKO ČRV",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "60941",
    "name": "SESTAVA IN MONTAŽA KOVINSKIH KONSTRUKCIJ BOŽO PETRIČ S.P.",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "61600",
    "name": "UROŠ ČERNIGOJ",
    "address": "",
    "postal": "5263 Dobravlje",
    "phone": "",
    "email": ""
  },
  {
    "code": "62652",
    "name": "S4S TRAVEL AGENCY, TURISTIČNA AGENCIJA, D.O.O.",
    "address": "",
    "postal": "6258 PRESTRANEK",
    "phone": "",
    "email": ""
  },
  {
    "code": "63594",
    "name": "TRANSPORT MITJA MITJA POŽENEL S.P.",
    "address": "",
    "postal": "5274 Črni Vrh nad Idrijo",
    "phone": "",
    "email": "mitja.pozenel@gmail.com"
  },
  {
    "code": "63676",
    "name": "mikuž andrej",
    "address": "",
    "postal": "5273 Col",
    "phone": "040148668",
    "email": "andrej.mikuz@gmail.com"
  },
  {
    "code": "64416",
    "name": "GO",
    "address": "",
    "postal": "5000 Nova Gorica",
    "phone": "predračun!",
    "email": "infogosky@gmail.com"
  },
  {
    "code": "64700",
    "name": "GA Adriatic d.o.o.",
    "address": "",
    "postal": "8000 NOVO MESTO",
    "phone": "00386 1 472 33 16",
    "email": "borna.muzevic@grandautomotive.eu"
  },
  {
    "code": "65667",
    "name": "MATEVŽ OREL",
    "address": "",
    "postal": "5295 Branik",
    "phone": "",
    "email": ""
  },
  {
    "code": "66457",
    "name": "TRANSPORT LUPO LUCIJAN VOVK S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "7",
    "email": "transportlupo@gmail.com"
  },
  {
    "code": "66951",
    "name": "POHORJE TURIZEM D.O.O. Dostava:Gorazd Smogavec Zg.Ložnica 1,2316 Zg.Lozni",
    "address": "",
    "postal": "2310 Slovenska Bistrica",
    "phone": "",
    "email": "info@pohorje-turizem.com"
  },
  {
    "code": "67533",
    "name": "GOZDARSTVO MAZI BLAŽ MAZI S.P.",
    "address": "",
    "postal": "1352 Preserje",
    "phone": "",
    "email": ""
  },
  {
    "code": "6770",
    "name": "ŠTRUKELJ MIT,D.O.O.,ŠEMPAS",
    "address": "",
    "postal": "5261 Šempas",
    "phone": "05 3077200",
    "email": "strukelj.mit@siol.net"
  },
  {
    "code": "67972",
    "name": "ZIDARSTVO IN STORITVE Z ROVOKOPAČEM ALEKSANDER REŠETA S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "aljaz.reseta@gmail.com"
  },
  {
    "code": "68011",
    "name": "ALEŠ BRATOVŠ",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "69588",
    "name": "KARBIDA FORS D.O.O.",
    "address": "",
    "postal": "3342 Gornji Grad",
    "phone": "",
    "email": "blaz.krznar@gmail.com"
  },
  {
    "code": "70036",
    "name": "Branko Kravos branko kravos s.p.",
    "address": "",
    "postal": "5295 Branik",
    "phone": "051328373",
    "email": "jcneeee@gmail.com"
  },
  {
    "code": "739",
    "name": "EUROTON, D.O.O.",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "01 530 30 00",
    "email": "fani.kimovec@euroton.si"
  },
  {
    "code": "74079",
    "name": "VZDRŽEVANJE IN POPRAVILA MOTORNIH VOZIL MS SPORT MITJA SLEJKO S.P.",
    "address": "",
    "postal": "5294 Dornberk",
    "phone": "041485972",
    "email": "mitja.slejko@gmail.com"
  },
  {
    "code": "75183",
    "name": "VALE AS, POSREDNIŠTVO PRI PRODAJI, D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "info@vale.si"
  },
  {
    "code": "75252",
    "name": "Praček Juraj",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "040888642",
    "email": "preček16@gmail.com"
  },
  {
    "code": "75747",
    "name": "AGROMEDICA STORITVE PRODAJA IN PROIZVODNJA D.O.O.",
    "address": "",
    "postal": "9250 GORNJA RADGONA",
    "phone": "",
    "email": ""
  },
  {
    "code": "770",
    "name": "SAVA AVTO D.O.O., TRGOVSKO, PROIZVODNO, SERVISNO PODJETJE SEVNICA",
    "address": "",
    "postal": "8294 Boštanj",
    "phone": "07 816 33 20",
    "email": "nabava@sava-avto.si;milan@sava-avto.si"
  },
  {
    "code": "78540",
    "name": "BOŠTJAN PREMRL",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "+38631873511",
    "email": "bostjan.premrl@gmail.com"
  },
  {
    "code": "79201",
    "name": "TOMAŽ JAMŠEK S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 368 0191",
    "email": "tomi.jamsek@siol.net"
  },
  {
    "code": "80773",
    "name": "VULKANIZERSTVO FURLAN D.O.O.",
    "address": "",
    "postal": "8257 Dobova",
    "phone": "07 452 2010",
    "email": "info@vulkanizerstvo-furlan.com"
  },
  {
    "code": "8190",
    "name": "KETE D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05-365-95-10",
    "email": "andreja@kete.si"
  },
  {
    "code": "82575",
    "name": "TRANSGRADNJA KOBAL D.O.O.",
    "address": "",
    "postal": "5273 Col",
    "phone": "7",
    "email": "ukobal1@gmail.com;ivan.kobal18@gmail.com"
  },
  {
    "code": "82983",
    "name": "VITIS D.O.O. BUDANJE",
    "address": "",
    "postal": "5271 Vipava",
    "phone": "",
    "email": ""
  },
  {
    "code": "84728",
    "name": "AVTOLIČARSTVO",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "05 3642574",
    "email": ""
  },
  {
    "code": "86667",
    "name": "ISISTEMI PRODAJA IN SERVIS RAČUNALNIKOV, TELEFONIJE, D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "7",
    "email": "info@isistemi.si"
  },
  {
    "code": "86895",
    "name": "POPRAVILO TRAKTORJEV TADEJ ZORN S.P.",
    "address": "",
    "postal": "5292 Renče",
    "phone": "4",
    "email": "jani.zorn12@gmail.com"
  },
  {
    "code": "86938",
    "name": "FALANGAPLUS ZAPOSLITVENA AGENCIJA D.O.O.",
    "address": "",
    "postal": "6000 Koper",
    "phone": "",
    "email": ""
  },
  {
    "code": "92063",
    "name": "JOKR TRANSPORT, TRGOVINA, GOSTINSTVO D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "041 613 813",
    "email": "jokr@amis.net"
  },
  {
    "code": "94365",
    "name": "TJAŠ KOMPARE S.P.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": ""
  },
  {
    "code": "95221",
    "name": "PREVOZI POTNIKOV JOŽE HOČEVAR S.P.",
    "address": "",
    "postal": "6222 Štanjel",
    "phone": "1",
    "email": "j.hocevar.39@gmail.com"
  },
  {
    "code": "96126",
    "name": "KLIMAVIDIC D.O.O.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "053680210",
    "email": "klimavidic@siol.net"
  },
  {
    "code": "97706",
    "name": "TOMAŽ FABČIČ",
    "address": "",
    "postal": "5272 Podnanos",
    "phone": "",
    "email": ""
  },
  {
    "code": "98976",
    "name": "DŽANNY KURIRSKE STORITVE DŽEVAD HALKIĆ S.P.",
    "address": "",
    "postal": "1000 LJUBLJANA",
    "phone": "//",
    "email": ""
  },
  {
    "code": "99468",
    "name": "Jernej Rojc",
    "address": "",
    "postal": "5294 Dornberk",
    "phone": "031893652",
    "email": "rojcjernejko@gmail.com"
  },
  {
    "code": "72322",
    "name": "Črnigoj Dejan",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "040202045",
    "email": "dejan.crnigoj@gmail.com"
  },
  {
    "code": "67742",
    "name": "SNICA TGS d.o.o.",
    "address": "",
    "postal": "5270 Ajdovščina",
    "phone": "",
    "email": "tadejmarc@gmail.com"
  }
]

@import_bp.route('/uvozi-stranke', methods=['GET', 'POST'])
@login_required
def uvozi_stranke():
    if not current_user.is_admin:
        return 'Samo admin.', 403
    uvozenih = 0
    preskocenih = 0
    for c in CUSTOMERS_DATA:
        existing = Customer.query.filter(Customer.name.ilike(c['name'])).first()
        if existing:
            preskocenih += 1
            continue
        customer = Customer(
            customer_code = c['code'],
            name          = c['name'],
            address       = c['address'],
            postal        = c['postal'],
            phone         = c['phone'],
            email         = c['email'],
        )
        db.session.add(customer)
        uvozenih += 1
    db.session.commit()
    return f'<h2>Uvoz zaključen!</h2><p>Uvoženih: {uvozenih}</p><p>Preskočenih (že obstajajo): {preskocenih}</p><a href="/customers/">Pojdi na stranke</a>'