# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# Used/unused kanji list code originally by 'LaC'
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import unicodedata
from anki.utils import ids2str, splitFields
from aqt.webview import AnkiWebView
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom
from .notetypes import isJapaneseNoteType
from aqt import mw
config = mw.addonManager.getConfig(__name__)

# Backwards compatibility
try:
    UNICODE_EXISTS = bool(type(unicode)) # Python 2.X
except NameError:
    unicode = lambda *s: str(s) # Python 3+
try:
    range = xrange # Python 2.X
except NameError:
    pass # Python 3+

def isKanji(unichar):
    try:
        return unicodedata.name(unichar).find('CJK UNIFIED IDEOGRAPH') >= 0
    except ValueError:
        # a control character
        return False

class KanjiStats(object):

    def __init__(self, col, wholeCollection):
        self.col = col
        if wholeCollection:
            self.lim = ""
        else:
            self.lim = " and c.did in %s" % ids2str(self.col.decks.active())
        self._gradeHash = dict()
        for (name, chars), grade in zip(self.kanjiGrades,
                                        range(len(self.kanjiGrades))):
            for c in chars:
                self._gradeHash[c] = grade

    def kanjiGrade(self, unichar):
        return self._gradeHash.get(unichar, 0)

    # FIXME: as it's html, the width doesn't matter
    def kanjiCountStr(self, gradename, count, total=0, width=0):
        d = {'count': self.rjustfig(count, width), 'gradename': gradename}
        if total:
            d['total'] = self.rjustfig(total, width)
            d['percent'] = float(count)/total*100
            return ("%(gradename)s: %(count)s of %(total)s (%(percent)0.1f%%).") % d
        else:
            return ("%(count)s %(gradename)s kanji.") % d

    def rjustfig(self, n, width):
        n = unicode(n)
        return n + "&nbsp;" * (width - len(n))

    def genKanjiSets(self):
        self.kanjiSets = [set([]) for g in self.kanjiGrades]
        chars = set()
        for m in self.col.models.all():
            _noteName = m['name'].lower()
            if not isJapaneseNoteType(_noteName):
                continue

            idxs = []
            for c, name in enumerate(self.col.models.fieldNames(m)):
                for f in config['srcFields']:
                    if name == f:
                        idxs.append(c)
            for row in self.col.db.execute("""
select flds from notes where id in (
select n.id from cards c, notes n
where c.nid = n.id and mid = ? and c.queue > 0
%s) """ % self.lim, m['id']):
                flds = splitFields(row[0])
                for idx in idxs:
                    chars.update(flds[idx])
        for c in chars:
            if isKanji(c):
                self.kanjiSets[self.kanjiGrade(c)].add(c)

    def report(self):
        self.genKanjiSets()
        counts = [(name, len(found), len(all)) \
                  for (name, all), found in zip(self.kanjiGrades, self.kanjiSets)]
        out = ((("<h1>Kanji statistics</h1>The seen cards in this %s "
                 "contain:") % (self.lim and "deck" or "collection")) +
               "<ul>" +
               # total kanji
               ("<li>%d total unique kanji.</li>") %
               sum([c[1] for c in counts]))

        out += "</ul><p/>" + (u"JLPT levels:") + "<p/><ul>"
        L = ["<li>" + self.kanjiCountStr(c[0],c[1],c[2], width=3) + "</li>"
             for c in counts[1:8]]
        out += "".join(L)
        out += "</ul>"
        return out

    def missingReport(self, check=None):
        if not check:
            check = lambda x, y: x not in y
            out = ("<h1>Missing</h1>")
        else:
            out = ("<h1>Seen</h1>")
        for grade in range(1, len(self.kanjiGrades)):
            missing = "".join(self.missingInGrade(grade, check))
            if not missing:
                continue
            out += "<h2>" + self.kanjiGrades[grade][0] + "</h2>"
            out += "<font size=+2>"
            out += self.mkEdict(missing)
            out += "</font>"
        return out + "<br/>"

    def mkEdict(self, kanji):
        out = "<font size=+2>"
        while 1:
            if not kanji:
                out += "</font>"
                return out
            # edict will take up to about 10 kanji at once
            out += self.edictKanjiLink(kanji[0:10])
            kanji = kanji[10:]

    def seenReport(self):
        return self.missingReport(lambda x, y: x in y)

    def nonJouyouReport(self):
        out = ("<h1>Non-Jouyou</h1>")
        out += self.mkEdict("".join(self.kanjiSets[0]))
        return out + "<br/>"

    def edictKanjiLink(self, kanji):
        base="http://nihongo.monash.edu/cgi-bin/wwwjdic?1MMJ"
        url=base + kanji
        return '<a href="%s">%s</a>' % (url, kanji)

    def missingInGrade(self, gradeNum, check):
        existingKanji = self.kanjiSets[gradeNum]
        totalKanji = self.kanjiGrades[gradeNum][1]
        return [k for k in totalKanji if check(k, existingKanji)]

    kanjiGrades = [
        (u'non-jouyou', ''),
        (u'JLPT 5', u'一右雨円下何火外学間気休金九月見五午後語校行高国今左三山四子時七車十出書女小上食人水生西先千川前大男中長天電土東読南二日入年白八半百父分聞母北本毎万名木友来六話'),
        (u'JLPT 4', u'悪安以医員飲院運映英駅屋音夏家歌花画会海界開楽漢館帰起急究牛去魚京強教業近銀空兄計建犬研験元言古公口工広考黒作仕使始姉思止死私紙試事字持自室質写社者借主手秋終習週集住重春少場色心新真親図世正青赤切早走送足族多体待貸代台題知地茶着昼注朝町鳥通弟店転田度冬答動同堂道特肉買売発飯病品不風服物文別勉歩方妹味明目問夜野有夕曜洋用理立旅料力'),
        (u'JLPT 3', u'愛暗位偉易違育因引泳越園演煙遠押横王化加果過解回皆絵害格確覚掛割活寒完官感慣観関顔願危喜寄幾期機記疑客吸求球給居許供共恐局曲勤苦具偶靴君係形景経警迎欠決件権険原現限呼互御誤交候光向好幸更構港降号合刻告込困婚差座最妻才歳済際在罪財昨察殺雑参散産賛残市指支歯似次治示耳辞式識失実若取守種酒首受収宿術処初所緒助除勝商招消笑乗常情状職信寝深申神進吹数制性成政晴精声静席昔石積責折説雪絶戦洗船選然全組想争相窓草増側息束速続存他太打対退宅達単探断段談値恥置遅調頂直追痛定庭程適点伝徒渡登都努怒倒投盗当等到逃頭働得突内難任認猫熱念能破馬敗杯背配箱髪抜判反犯晩番否彼悲疲費非飛備美必表貧付夫富怖浮負舞部福腹払平閉米変返便捕暮報抱放法訪亡忘忙望末満未民眠務夢娘命迷鳴面戻役約薬優由遊予余与容様葉要陽欲頼落利流留両良類例冷礼列連路労老論和逹'),
        (u'JLPT 2', u'圧依囲委移胃衣域印羽雲営栄永鋭液延塩汚央奥欧黄億温河荷菓課貨介快改械灰階貝各角革額乾刊巻干患換汗甘管簡缶丸含岸岩希机祈技喫詰逆久旧巨漁競協叫境挟橋況胸極玉均禁区隅掘訓群軍傾型敬軽芸劇血券県肩賢軒減個固庫戸枯湖雇効厚硬紅耕肯航荒講郊鉱香腰骨根混査砂再採祭細菜材坂咲冊刷札皿算伺刺枝糸脂詞誌児寺湿捨弱周州拾舟柔祝述準純順署諸召将床承昇焼照省章紹象賞城畳蒸植触伸森臣辛針震勢姓星清税隻籍績跡接設占専泉浅線双層捜掃燥総装像憎臓蔵贈造則測卒孫尊損村帯替袋濯谷担炭短団池築畜竹仲柱虫駐著貯兆庁超沈珍低停底泥滴鉄殿塗党凍塔島湯灯筒導童銅毒届曇鈍軟乳燃悩濃脳農波拝倍泊薄爆麦肌板版般販比皮被鼻匹筆氷秒瓶布普符膚武封副復幅複沸仏粉兵並片編辺補募包宝豊帽暴棒貿防磨埋枚綿毛門油輸勇郵預幼溶踊浴翌絡乱卵裏陸律略粒了涼療量領緑林輪涙令零齢歴恋練録湾腕'),
        (u'JLPT 1', u'亜阿哀葵茜握渥旭梓扱宛絢綾鮎案杏伊威尉惟慰為異緯遺井亥郁磯壱逸稲茨芋允姻胤陰隠韻烏卯丑渦唄浦瓜叡影瑛衛詠疫益悦謁閲宴怨援沿炎猿縁艶苑鉛於凹往応旺殴翁岡沖荻憶乙卸恩穏仮伽価可嘉嫁寡暇架禍稼箇茄華霞蚊我牙芽雅餓塊壊怪悔懐戒拐魁凱劾慨概涯街該馨垣嚇拡核殻獲穫較郭閣隔岳笠潟喝括渇滑褐轄且叶樺株蒲鎌茅刈瓦侃冠勘勧喚堪寛幹憾敢棺款歓環監看緩肝艦莞貫還鑑閑陥韓巌眼頑企伎器基奇嬉岐忌揮旗既棋棄毅汽稀貴軌輝飢騎鬼亀偽宜戯擬欺犠誼菊鞠吉橘却脚虐丘及宮弓救朽泣窮級糾拒拠挙虚距亨享凶匡喬峡恭狂狭矯脅興郷鏡響驚仰凝尭暁桐錦斤欣欽琴筋緊芹菌衿襟謹吟玖駆駒愚虞遇串屈窪熊栗繰桑勲薫郡袈刑啓圭契径恵慶慧憩掲携桂渓系継茎蛍鶏鯨撃激傑潔穴結倹健兼剣圏堅嫌憲懸拳検献絹謙遣顕厳幻弦源玄絃孤己弧故胡虎誇顧鼓伍呉吾娯悟梧瑚碁護乞鯉侯倖功后坑孔孝宏巧康弘恒慌抗拘控攻昂晃江洪浩溝甲皇稿紘絞綱衡貢購酵鋼項鴻剛拷豪克穀酷獄墾恨懇昆紺魂唆嵯沙瑳詐鎖裟債催哉宰彩栽災采砕斎裁載剤冴阪崎埼削搾朔策索錯桜笹撮擦皐傘惨桟燦蚕酸暫司姿志施旨氏祉紫肢至視諮賜雌飼侍慈爾磁蒔汐鹿軸執漆疾偲芝舎射赦斜煮紗謝遮蛇邪勺尺爵酌釈寂朱殊狩珠趣儒寿授樹需囚宗就修愁洲秀臭衆襲酬醜充従汁渋獣縦銃叔淑縮粛塾熟俊峻瞬竣舜駿准循旬殉淳潤盾巡遵暑曙渚庶叙序徐恕傷償匠升唱奨宵尚庄彰抄掌捷昌昭晶松梢沼渉焦症硝礁祥称粧肖菖蕉衝裳訟証詔詳鐘障丈丞冗剰壌嬢条浄穣譲醸錠嘱飾殖織辱侵唇娠審慎振晋榛浸秦紳薪診身仁刃尋甚尽迅陣須酢垂帥推炊睡粋翠衰遂酔錘随瑞髄崇嵩枢雛据杉澄寸瀬畝是征整牲盛聖製誠誓請逝斉惜斥析碩拙摂窃節舌仙宣扇栓染潜旋繊羨薦践遷銭銑鮮善漸禅繕塑措曽疎礎租粗素訴阻僧創倉喪壮奏爽惣挿操曹巣槽漕綜聡荘葬蒼藻遭霜騒促即俗属賊袖汰堕惰駄耐怠態泰滞胎逮隊黛鯛第鷹滝卓啄択拓沢琢託濁諾只但辰奪脱巽棚丹嘆旦淡端胆誕鍛壇弾暖檀痴稚致蓄逐秩窒嫡宙忠抽衷鋳猪丁帳弔張彫徴懲挑暢潮眺聴脹腸蝶跳勅朕賃鎮陳津墜椎塚槻漬辻蔦椿坪紬爪釣鶴亭偵貞呈堤帝廷悌抵提禎締艇訂逓邸摘敵的笛哲徹撤迭典展添吐斗杜賭奴刀唐悼搭桃棟痘糖統藤討謄豆踏透陶騰闘憧洞瞳胴峠匿徳督篤独栃凸寅酉屯惇敦豚奈那凪捺縄楠尼弐虹廿如尿妊忍寧粘乃之納巴把覇派婆俳廃排肺輩培媒梅賠陪萩伯博拍柏舶迫漠縛函肇畑鉢伐罰閥鳩隼伴帆搬班畔繁藩範煩頒盤蛮卑妃扉批披斐泌碑秘緋罷肥避尾微眉柊彦菱姫媛俵彪標漂票評描苗彬浜賓頻敏扶敷腐譜賦赴附侮楓蕗伏覆噴墳憤奮紛雰丙併塀幣弊柄陛頁壁癖碧偏遍弁保穂墓慕簿倣俸奉峰崩朋泡砲縫胞芳萌褒邦飽鳳鵬乏傍剖坊妨房某冒紡肪膨謀僕墨撲朴牧睦没堀幌奔翻凡盆摩魔麻槙幕膜柾亦又抹沫繭麿慢漫魅巳岬密蜜稔脈妙無矛霧椋婿盟銘滅免模茂妄孟猛盲網耗黙勿紋匁也冶耶弥矢厄訳躍靖柳愉癒諭唯佑宥幽悠憂柚湧猶祐裕誘邑雄融誉庸揚揺擁楊窯羊耀蓉謡遥養抑翼羅裸雷酪嵐欄濫藍蘭覧履李梨痢里離率琉硫隆竜慮虜亮僚凌寮猟瞭稜糧諒遼陵倫厘琳臨隣麟瑠塁累伶励嶺怜玲鈴隷霊麗暦劣烈裂廉蓮錬呂炉露廊朗楼浪漏郎禄倭賄脇惑枠亘侑勁匕奎嬌崚彗昴晏晨晟暉曰栞椰毬洸洵滉漱澪燎燿瑶皓眸笙綺綸翔脩茉莉菫詢諄赳迪頌颯黎凜熙')
        ]

def genKanjiStats():
    wholeCollection = mw.state == "deckBrowser"
    s = KanjiStats(mw.col, wholeCollection)
    rep = s.report()
    rep += s.seenReport()
    rep += s.missingReport()
    rep += s.nonJouyouReport()
    return rep

def onKanjiStats():
    mw.progress.start(immediate=True)
    rep = genKanjiStats()
    d = QDialog(mw)
    l = QVBoxLayout()
    l.setContentsMargins(0,0,0,0)
    w = AnkiWebView()
    l.addWidget(w)
    w.stdHtml(rep)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    l.addWidget(bb)
    bb.rejected.connect(d.reject)
    d.setLayout(l)
    d.resize(500, 400)
    restoreGeom(d, "kanjistats")
    mw.progress.finish()
    d.exec_()
    saveGeom(d, "kanjistats")

def createMenu():
    a = QAction(mw)
    a.setText("Kanji JLPT Stats")
    mw.form.menuTools.addAction(a)
    a.triggered.connect(onKanjiStats)

createMenu()
