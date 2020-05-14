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
               # total kanji unique
               ("<li>%d total unique kanji.</li>") %
               sum([c[1] for c in counts]))
        count = sum([c[1] for c in counts])
        d = {'count': self.rjustfig(count, 3)}
        total = sum([c[2] for c in counts])
        d['total'] = self.rjustfig(total,3)
        d['percent'] = float(count/total*100)
        out += ("<li>Total : %(count)s of %(total)s (%(percent)0.1f%%).</li>") % d
		#Most Used
        out += "</ul><p/>" + (u"Most Used :") + "<p/><ul>"
        L = ["<li>" + self.kanjiCountStr(c[0],c[1],c[2], width=3) + "</li>"
			for c in counts[1:26]]
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
		(u'1-100 most used', u'日一国会人年大十二本中長出三同時政事自行社見月分議後前民生連五発間対上部東者党地合市業内相方四定今回新場金員九入選立開手米力学問高代明実円関決子動京全目表戦経通外最言氏現理調体化田当八六約主題下首意法'),
		(u'101-200 most used', u'不来作性的要用制治度務強気小七成期公持野協取都和統以機平総加山思家話世受区領多県続進正安設保改数記院女初北午指権心界支第産結百派点教報済書府活原先共得解名交資予川向際査勝面委告軍文反元重近千考判認画海'),
        (u'201-300 most used', u'参売利組知案道信策集在件団別物側任引使求所次水半品昨論計死官増係感特情投示変打男基私各始島直両朝革価式確村提運終挙果西勢減台広容必応演電歳住争談能無再位置企真流格有疑口過局少放税検藤町常校料沢裁状工建'),
		(u'301-400 most used',u'語球営空職証土与急止送援供可役構木割聞身費付施切由説転食比難防補車優夫研収断井何南石足違消境神番規術護展態導鮮備宅害配副算視条幹独警宮究育席輸訪楽起万着乗店述残想線率病農州武声質念待試族象銀域助労例衛'),
		(u'401-500 most used', u'然早張映限親額監環験追審商葉義伝働形景落欧担好退準賞訴辺造英被株頭技低毎医復仕去姿味負閣韓渡失移差衆個門写評課末守若脳極種美岡影命含福蔵量望松非撃佐核観察整段横融型白深字答夜製票況音申様財港識注呼渉達'),        (u'501-600 most used',u'良響阪帰針専推谷古候史天階程満敗管値歌買突兵接請器士光討路悪科攻崎督授催細効図週積丸他及湾録処省旧室憲太橋歩離岸客風紙激否周師摘材登系批郎母易健黒火戸速存花春飛殺央券赤号単盟座青破編捜竹除完降超責並療'),
		(u'601-700 most used',u'従右修捕隊危採織森競拡故館振給屋介読弁根色友苦就迎走販園具左異歴辞将秋因献厳馬愛幅休維富浜父遺彼般未塁貿講邦舞林装諸夏素亡劇河遣航抗冷模雄適婦鉄寄益込顔緊類児余禁印逆王返標換久短油妻暴輪占宣背昭廃植熱'),
		(u'701-800 most used',u'宿薬伊江清習険頼僚覚吉盛船倍均億途圧芸許皇臨踏駅署抜壊債便伸留罪停興爆陸玉源儀波創障継筋狙帯延羽努固闘精則葬乱避普散司康測豊洋静善逮婚厚喜齢囲卒迫略承浮惑崩順紀聴脱旅絶級幸岩練押軽倒了庁博城患締等救執'),
		(u'801-900 most used',u'層版老令角絡損房募曲撤裏払削密庭徒措仏績築貨志混載昇池陣我勤為血遅抑幕居染温雑招奈季困星傷永択秀著徴誌庫弾償刊像功拠香欠更秘拒刑坂刻底賛塚致抱繰服犯尾描布恐寺鈴盤息宇項喪伴遠養懸戻街巨震願絵希越契掲躍'),
		(u'901-1000 most used',u'棄欲痛触邸依籍汚縮還枚属笑互複慮郵束仲栄札枠似夕恵板列露沖探逃借緩節需骨射傾届曜遊迷夢巻購揮君燃充雨閉緒跡包駐貢鹿弱却端賃折紹獲郡併草徹飲貴埼衝焦奪雇災浦暮替析預焼簡譲称肉納樹挑章臓律誘紛貸至宗促慎控'),
		(u'1001-1100 most used',u'贈智握照宙酒俊銭薄堂渋群銃悲秒操携奥診詰託晴撮誕侵括掛謝双孝刺到駆寝透津壁稲仮暗裂敏鳥純是飯排裕堅訳盗芝綱吸典賀扱顧弘看訟戒祉誉歓勉奏勧騒翌陽閥甲快縄片郷敬揺免既薦隣悩華泉御範隠冬徳皮哲漁杉里釈己荒貯'),
		(u'1101-1200 most used',u'硬妥威豪熊歯滞微隆埋症暫忠倉昼茶彦肝柱喚沿妙唱祭袋阿索誠忘襲雪筆吹訓懇浴俳童宝柄驚麻封胸娘砂李塩浩誤剤瀬趣陥斎貫仙慰賢序弟旬腕兼聖旨即洗柳舎偽較覇兆床畑慣詳毛緑尊抵脅祝礼窓柔茂犠旗距雅飾網竜詩昔繁殿濃'),
		(u'1201-1300 most used',u'翼牛茨潟敵魅嫌魚斉液貧敷擁衣肩圏零酸兄罰怒滅泳礎腐祖幼脚菱荷潮梅泊尽杯僕桜滑孤黄煕炎賠句寿鋼頑甘臣鎖彩摩浅励掃雲掘縦輝蓄軸巡疲稼瞬捨皆砲軟噴沈誇祥牲秩帝宏唆鳴阻泰賄撲凍堀腹菊絞乳煙縁唯膨矢耐恋塾漏紅慶'),
		(u'1301-1400 most used',u'猛芳懲郊剣腰炭踊幌彰棋丁冊恒眠揚冒之勇曽械倫陳憶怖犬菜耳潜珍梨仁克岳概拘墓黙須偏雰卵遇湖諮狭喫卓干頂虫刷亀糧梶湯箱簿炉牧殊殖艦溶輩穴奇慢鶴謀暖昌拍朗丈鉱寛覆胞泣涙隔浄匹没暇肺孫貞靖鑑飼陰銘鋭随烈尋渕稿'),
		(u'1401-1500 most used',u'枝丹啓也丘棟壌漫玄粘悟舗妊塗熟軒旭恩毒騰往豆遂晩狂叫栃岐陛緯培衰艇屈径淡抽披廷錦准暑拝磯奨妹浸剰胆氷繊駒乾虚棒寒孜霊帳悔諭祈惨虐翻墜沼据肥徐糖搭姉髪忙盾脈滝拾軌俵妨盧粉擦鯨漢糸荘諾雷漂懐勘綿栽才拐笠駄'),
		(u'1501-1600 most used',u'添汗冠斜銅鏡聡浪亜覧詐壇勲魔酬紫湿曙紋卸奮趙欄逸涯拓眼瓶獄筑尚阜彫咲穏顕巧矛垣召欺釣缶萩粧隻葛脂粛栗愚蒸嘉遭架篠鬼庶肌稚靴菅滋幻煮姫誓耕把践呈疎仰鈍恥剛疾征砕謡嫁謙后嘆俣菌鎌巣泥頻琴班淵棚潔酷宰廊寂辰'),
		(u'1601-1700 most used',u'隅偶霞伏灯柏辛磨碁俗漠邪晶辻麦墨鎮洞履劣那殴娠奉憂朴亭姓淳荻筒鼻嶋怪粒詞鳩柴偉酔惜穫佳潤悼乏胃該赴桑桂髄虎盆晋穂壮堤飢傍疫累痴搬畳晃癒桐寸郭机尿凶吐宴鷹賓虜膚陶鐘憾畿猪紘磁弥昆粗訂芽尻庄傘敦騎寧濯循忍'),
		(u'1701-1800 most used',u'磐猫怠如寮祐鵬塔沸鉛珠凝苗獣哀跳灰匠菓垂蛇澄縫僧幾眺唐亘呉凡憩鄭芦龍媛溝恭刈睡錯伯帽笹穀柿陵霧魂枯弊釧妃舶餓腎窮掌麗綾臭釜悦刃縛暦宜盲粋辱毅轄猿弦嶌稔窒炊洪摂飽函冗涼桃狩舟貝朱渦紳枢碑鍛刀鼓裸鴨符猶塊'),
		(u'1801-1900 most used',u'旋弓幣膜扇脇腸憎槽鍋慈皿肯樋楊伐駿漬燥糾亮墳坪畜紺慌娯吾椿舌羅坊峡俸厘峰圭醸蓮弔乙倶汁尼遍堺衡呆薫瓦猟羊窪款閲雀偵喝敢畠胎酵憤豚遮扉硫赦挫挟窃泡瑞又慨紡恨肪扶戯伍忌濁奔斗蘭蒲迅肖鉢朽殻享秦茅藩沙輔曇媒'),
		(u'1901-2000 most used',u'鶏禅嘱胴粕冨迭挿湘嵐椎灘堰獅姜絹陪剖譜郁悠淑帆暁鷲傑楠笛芥其玲奴誰錠拳翔遷拙侍尺峠篤肇渇榎俺劉幡諏叔雌亨堪叙酢吟逓痕嶺袖甚喬崔妖琵琶聯蘇闇崇漆岬癖愉寅捉礁乃洲屯樽樺槙薩姻巌淀麹賭擬塀唇睦閑胡幽峻曹哨詠'),
		(u'2001-2100 most used',u'炒屏卑侮鋳抹尉槻隷禍蝶酪茎汎頃帥梁逝滴汽謎琢箕匿爪芭逗苫鍵襟蛍楢蕉兜寡琉痢庸朋坑姑烏藍僑賊搾奄臼畔遼唄孔橘漱呂桧拷宋嬢苑巽杜渓翁藝廉牙謹瞳湧欣窯褒醜魏篇升此峯殉煩巴禎枕劾菩堕丼租檜稜牟桟榊錫荏惧倭婿慕'),
		(u'2101-2200 most used',u'廟銚斐罷矯某囚魁薮虹鴻泌於赳漸逢凧鵜庵膳蚊葵厄藻萬禄孟鴈狼嫡呪斬尖翫嶽尭怨卿串已嚇巳凸暢腫粟燕韻綴埴霜餅魯硝牡箸勅芹杏迦棺儒鳳馨斑蔭焉慧祇摯愁鷺楼彬袴匡眉苅讃尹欽薪湛堆狐褐鴎瀋挺賜嵯雁佃綜繕狛壷橿栓翠'),
		(u'2201-2300 most used',u'鮎芯蜜播榛凹艶帖伺桶惣股匂鞍蔦玩萱梯雫絆錬湊蜂隼舵渚珂煥衷逐斥稀癌峨嘘旛篭芙詔皐雛娼篆鮫椅惟牌宕喧佑蒋樟耀黛叱櫛渥挨憧濡槍宵襄妄惇蛋脩笘宍甫酌蚕壕嬉囃蒼餌簗峙粥舘銕鄒蜷暉捧頒只肢箏檀鵠凱彗謄諌樫噂脊牝'),
		(u'2301-2400 most used',u'梓洛醍砦丑笏蕨噺抒嗣隈叶凄汐絢叩嫉朔蔡膝鍾仇伽夷恣瞑畝抄杭寓麺戴爽裾黎惰坐鍼蛮塙冴旺葦礒咸萌饗歪冥偲壱瑠韮漕杵薔膠允眞蒙蕃呑侯碓茗麓瀕蒔鯉竪弧稽瘤澤溥遥蹴或訃矩厦冤剥舜侠贅杖蓋畏喉汪猷瑛搜曼附彪撚噛卯'),
		(u'2401-2501 most used',u'桝撫喋但溢闊藏浙彭淘剃揃綺徘巷竿蟹芋袁舩拭茜凌頬厨犀簑皓甦洸毬檄姚蛭婆叢椙轟贋洒貰儲緋貼諜鯛蓼甕喘怜溜邑鉾倣碧燈諦煎瓜緻哺槌啄穣嗜偕罵酉蹄頚胚牢糞悌吊楕鮭乞倹嗅詫鱒蔑轍醤惚廣藁柚舛縞謳杞鱗繭釘弛狸壬硯蝦')
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
    a.setText("Most Used Kanji Stats")
    mw.form.menuTools.addAction(a)
    a.triggered.connect(onKanjiStats)

createMenu()
