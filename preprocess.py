import regex as re
import gradio as gr
from collections import Counter
import cn2an
from difflib import Differ
from gradio import update as gu


def diff_texts(text1, text2):
    d = Differ()
    return [(t[2:], '添加部分' if t[0] == '+' else '删除部分' if t[0] == '-' else None) for t in d.compare(text1, text2)]


normalizer = lambda x: cn2an.transform(x, "an2cn")


rep_map = {
    ":": "：",
    "∶": "：",
    ";": "；",
    ",": "，",
    ".": "。",
    "．": "。",
    "!": "！",
    "?": "？",
    "(": "（",
    ")": "）",
    "【": "（",
    "】": "）",
    "[": "（",
    "]": "）",
    "〖": "（",
    "〗": "）",
    "{": "（",
    "}": "）",
    "─": "—",
    "-": "—",
    "―": "—",
    "～": "—",
    "~": "—",
    "┅": '…',
    "　": '',
    " ": '',
    "\t": '',
}
h = ''
f = ''


def remove_inner_brackets(text):
    stack = []
    result = []
    for char in text:
        if char == '【':
            if not stack:
                result.append(char)
            stack.append(char)
        elif char == '】':
            stack.pop()
            if not stack:
                result.append(char)
        else:
            result.append(char)
    return ''.join(result)


def short_text(text):
    text = re.sub(r'⦅.*?⦆', '', text)
    return (text[:12] + '...' + text[-12:]) if len(text) > 25 else text


def process_text1(text0, final=True):
    text0 = re.sub(r'⦅.*?⦆', '', text0)
    text00 = text0
    text1 = ''
    if m := re.search('(（(?:笑声|深吸|吸鼻).*?\d.*?）)', text00):
        l = m.group(1)
        t, text00 = text00.split(l, 1)
        text1 += normalizer(t) + l
    text1 += normalizer(text00)

    if text1 == text0:
        log1 = '1 数字转汉字【成功】：文本中未检测到数字，无需转换！'
        return text1, log1, gu(value=[[' ', None]], visible=False)
    else:
        log1 = '1 数字转汉字【成功】：文本检测到数字，已经转换！' + ('\n前后对比请查看高亮窗口！' if final else '')
        return text1, log1, gu(value=diff_texts(text0, text1), visible=True)


def process_text2(text0, final=True):
    text1, log, _ = process_text1(text0, final=False)
    text2 = text1.translate(str.maketrans(rep_map))
    text2 = re.sub(r'"{2,}', '"', text2)
    text2 = re.sub(r'\'{2,}', '\'', text2)
    text2 = re.sub(r'\n+', '\n', text2)
    text2 = re.sub(r'^\n', '', text2)
    text2 = re.sub(r'\。{2,}', '…', text2)
    text2 = re.sub(r'—{2,}', '——', text2)
    if text1 == text2:
        log += '\n2 特殊符号处理【成功】：标点符号无需规整！'
    else:
        log += '\n2 特殊符号处理【成功】：标点符号已经规整！'

    allowed_chars = re.compile(r'[\u4e00-\u9fff。，！？、；：「」『』\'“”_"‘’⦃⦄《》（）…—\n\d]')
    char_count = Counter([char for char in text2 if not allowed_chars.match(char)])
    spec = '  '.join(f"{char}({freq})" for char, freq in char_count.most_common())
    if spec:
        log += '\n以下特殊符号已经被移除，括号中为出现次数统计。\n' + spec
        text2 = ''.join(char for char in text2 if allowed_chars.match(char))

    text2 = re.sub(r'"{2,}', '"', text2)
    text2 = re.sub(r'\'{2,}', '\'', text2)
    text2 = re.sub(r'\n+', '\n', text2)
    text2 = re.sub(r'^\n', '', text2)
    text2 = re.sub(r'\。{2,}', '…', text2)
    text2 = re.sub(r'—{2,}', '——', text2)
    text2 = text2.replace('\n', '\n\n')
    if text1 == text2:
        return text2, log, gu(value=[[' ', None]], visible=False)
    else:
        log += '\n前后对比请查看高亮窗口！' if final else ''
        return text2, log, gu(value=diff_texts(text1, text2), visible=True)


def hl(text: str):
    text = remove_inner_brackets(text)
    out = []
    while text != '':
        if '【' in text:
            out += [(text.split('【')[0], None), (text.split('【', 1)[1].split('】')[0], '需检查修改')]
            text = text.split('】', 1)[1]
        else:
            out += [(text, None)]
            text = ''
    return [(x, '删除部分' if x.startswith('（') else y) for x, y in out]


def process_text3(text, op3=[], final=True):
    text = re.sub(r'⦅.*?⦆', '', text)
    remove_parenthesis = '删除括号与括号内文本' in op3
    across_multi_para = '引号内的内容允许换行' in op3
    text2, log, _ = process_text2(text, final=False)
    text3 = text2
    text3_hl = text3
    if ts := [t for t in text3.split('\n') if t.count('（') != t.count('）')]:
        log += '\n3-1 检查括号【失败】：以下段落内前后括号数量不一致，请修改后重新提交。无需修改空心括号中的提示信息\n' + '\n'.join(map(short_text, ts))
        for t in ts:
            text3 = re.sub(r'(?<!⦆)' + t, '⦅本段落内前后括号数量不一致，请检查修改⦆' + t, text3, 1)
            text3_hl = re.sub(r'(?<!】)' + t, f'【⦅本段落内前后括号数量不一致，请检查修改⦆{t}】', text3_hl, 1)
        return text3, log, gu(value=hl(text3_hl), visible=True)
    else:
        if remove_parenthesis:
            text3_ = re.sub(r'（(?:[^（）]*|(?R))*\）', '', text3)
            text3_hl = re.sub(r'(（(?:[^（）]*|(?R))*\）)', r'【\1】', text3)

            if text3_ == text3:
                log += '\n3-1 检查括号【成功】：没有检测到括号！'
            else:
                log += '\n3-1 检查括号【成功】：括号以及其内容已经删除！' + ('前后对比请查看高亮窗口！' if final else '')
            text3 = text3_
        else:
            log += '\n3-1 检查括号【成功】：括号无异常！'

    info = ''
    if across_multi_para:
        for x in ['“”', '‘’', '「」', '『』']:
            for i in [0, 1]:
                if ts := re.findall(f'{x[i]}[^{x[1-i]}]*?{x[i]}', text):
                    info += f'\n\n以下位置 {x[i]} 符号有嵌套现象，请修改后重新提交：\n' + '\n'.join([short_text(t) for t in ts])
                    for t in ts:
                        text3 = re.sub(r'(?<!⦆)' + t, f'⦅此符号有嵌套现象→⦆{t}⦅←此符号有嵌套现象⦆', text3, 1)
                        text3_hl = re.sub(r'(?<!】)' + t, f'【⦅此符号有嵌套现象→⦆{t[0]}】{t[1:-1]}【{t[-1]}⦅←此符号有嵌套现象⦆】', text3_hl, 1)
            if text.count(x[0]) != text.count(x[1]):
                info += f'\n\n全文 {x} 符号数量不匹配，请检查后重新提交！\n'
                text3_hl = text3_hl.replace(x[0], f'【{x[0]}】').replace(x[1], f'【{x[1]}】')

        for x in ['\'\"']:
            if text.count(x) % 2 == 1:
                info += f'\n\n全文 {x} 符号数量为奇数，请检查后重新提交！\n'
                text3_hl = text3_hl.replace(x, f'【{x}】')
    else:
        for x in ['“”', '‘’', '「」', '『』']:
            for i in [0, 1]:
                if ts := re.findall(f'{x[i]}[^{x[1-i]}\n]*?{x[i]}', text3):
                    info += f'\n\n以下位置 {x[i]} 符号有嵌套现象，请修改后重新提交：\n' + '\n'.join([short_text(t) for t in ts])
                    for t in ts:
                        text3 = re.sub(r'(?<!⦆)' + t, f'⦅此符号有嵌套现象→⦆{t}⦅←此符号有嵌套现象⦆', text3, 1)
                        text3_hl = re.sub(r'(?<!】)' + t, f'【⦅此符号有嵌套现象→⦆{t[0]}】{t[1:-1]}【{t[-1]}⦅←此符号有嵌套现象⦆】', text3_hl, 1)
        for x in ['“”', '‘’', '「」', '『』']:
            if ts := [t for t in text3.split('\n') if t.count(x[0]) != t.count(x[1])]:
                info += f'\n\n以下段落 {x} 符号数量不匹配，请检查后重新提交：\n' + '\n'.join([short_text(t) for t in ts])
            tmp_ = ''
            for t in text3.split('\n'):
                if t.count(x[0]) != t.count(x[1]):
                    tmp_ += f'⦅本段落 {x} 符号数量不匹配，请检查修改⦆' + t + '\n'
                else:
                    tmp_ += t + '\n'
            text3 = tmp_[:-1]
            tmp_ = ''
            for t in text3_hl.split('\n'):
                if t.count(x[0]) != t.count(x[1]):
                    tmp_ += f'【⦅本段落 {x} 符号数量不匹配，请检查修改⦆】' + t + '\n'
                else:
                    tmp_ += t + '\n'
            text3_hl = tmp_[:-1]
        for x in ['\'\"']:
            if ts := [t for t in text3.split('\n') if t.count(x) % 2 == 1]:
                info += f'\n\n以下段落中 {x} 符号数量为奇数，请检查后重新提交：\n' + '\n'.join([short_text(t) for t in ts])

            tmp_ = ''
            for t in text3.split('\n'):
                if t.count(x) % 2 == 1:
                    tmp_ += f'⦅本段落 {x} 符号数量为奇数，请检查修改⦆' + t + '\n'
                else:
                    tmp_ += t + '\n'
            text3 = tmp_[:-1]
            tmp_ = ''
            for t in text3_hl.split('\n'):
                if t.count(x) % 2 == 1:
                    tmp_ += f'【⦅本段落 {x} 符号数量为奇数，请检查修改⦆】' + t + '\n'
                else:
                    tmp_ += t + '\n'
            text3_hl = tmp_[:-1]

    if info:
        log += '\n3-2 检查引号【失败】：文本中引号存在错误！请查看以下信息：' + info
    else:
        log += '\n3-2 检查引号【成功】：文中引号无异常！'
    if text3 == text2:
        if text2 == text:
            return text3, log, gu(value=[[' ', None]], visible=False)
        else:
            return text3, log, gu(value=diff_texts(text, text3), visible=True)
    else:
        if info:
            return text3, log, gu(value=hl(text3_hl), visible=True)
        else:
            return text3, log, gu(value=diff_texts(text, text3), visible=True)


def process_text4(text, op3, op41, op421, tb421, op422, tb422, op423, tb423, op424, hl2_choices):
    text, log, gu_ = process_text3(text, op3, final=True)
    if '【失败】' in log:
        hl2_choices = []
        return text, log, gu_, [['对话分析失败，预处理存在问题！', None], ['\n', '候选但不是对话']], gu(choices=hl2_choices)
    log += '对话判断成功！如需调整对话部分，请修改原文与对话判断规则并重试。如有需要，请设置每句对话的音色。'
    text_ = text
    h = []
    h2e = {}
    for x in op41:
        if '：.' not in x:
            text_ = text_.replace('说：' + x[0], '〇：' + x[0]).replace('道：' + x[0], '〇：' + x[0])
            h += [x[0]]
            h2e[x[0]] = x[-1]
        else:
            h += [x[:2]]
            h2e[x[:2]] = '\n'
    houxuan = []
    s = 0
    while 1:
        hh = [None, len(text_)]
        for i in h:
            hi = text_.find(i)
            if hh[1] > hi > -1:
                hh = [i, hi]
        if hh[0] is None:
            break
        else:
            start = hh[1]
            le = text_[start:].find(h2e[hh[0]]) + 1
            start2 = hh[1] + (2 if '：' in hh[0] else 0)
            le2 = text_[start2:].find(h2e[hh[0]]) + 1
            if le2 != 0:
                houxuan.append([hh[0], s + start2, le2, text_[start2 : start2 + le2], '候选但不是对话'])
            s += le
            text_ = text_[:start] + text_[(start + le) :]

    for hou in houxuan:
        neibu = hou[3].replace(hou[0], '').replace(h2e[hou[0]], '')
        if op421 and neibu[-1] in tb421:
            hou[-1] = '对话（未选中）'
        if op422 and re.search(f'[{tb422}]', neibu):
            hou[-1] = '对话（未选中）'
        if op423 and text[hou[1] - 1] in tb423:
            hou[-1] = '对话（未选中）'
        if op424 and (hou[1] == 0 or text[hou[1] - 1] == '\n'):
            hou[-1] = '对话（未选中）'

    ss = 0
    hl = []
    idx = 1
    rep = []
    for q, s, le, t, l in houxuan:
        if s > ss:
            hl.append((text[ss:s], None))
        if l.startswith('对话'):
            t = text[s : s + le]
            if '⦃' not in t:
                if t[0] in h:
                    rep.append([t, f'{t[0]}⦃平均音色⦄{t[1:]}'])
                    t = f'{t[0]}⦃平均音色⦄{t[1:]}'
                else:
                    rep.append([t, f'⦃平均音色⦄{t}'])
                    t = f'⦃平均音色⦄{t}'
            hl.append((f'{idx}. {t}', l))
            idx += 1
        else:
            hl.append((text[s : s + le], l))
        ss = s + le

    if len(text) > ss:
        hl.append((text[ss : len(text)], None))
    for x, y in rep:
        text = text.replace(x, y, 1)

    hl2_choices = [t for t, _ in hl if '.' in t]
    return text, log, gu_, hl, gu([], choices=hl2_choices), hl2_choices


def process_text4_change(hl2_cb, hl2, hl2_choices):
    return [(x['token'], '对话（选中）' if x['token'] in hl2_cb else '对话（未选中）' if x['token'] in hl2_choices else x['class_or_confidence']) for x in hl2]


def process_text4_voice(ref, text_input, hl2, hl2_cb, hl2_choices):
    if len(hl2_choices) == 0:
        return gu(), gu(), gu()
    hl2_choices = [re.sub('⦃.*?⦄', f'⦃{ref}⦄', x) if x in hl2_cb else x for x in hl2_choices]
    hl2 = [
        (
            re.sub('⦃.*?⦄', f'⦃{ref}⦄', x['token']) if x['token'] in hl2_cb else x['token'],
            '对话（未选中）' if x['class_or_confidence'] and x['class_or_confidence'].startswith('对话') else x['class_or_confidence'],
        )
        for x in hl2
    ]
    text_input = ''.join([x.split('. ')[1] if '.' in x else x for x, y in hl2])
    return text_input, hl2, gu([], choices=hl2_choices), hl2_choices



def process_cut(hl2, pre, start_idx):
    # 。，！？、；：「」『』\'“”_"‘’⦃⦄《》（）…—\n
    if hl2 is None or len(hl2) == 0:
        return '请先执行对话判断！'
    out = []
    input = [hl2[0]['token']]
    for x in hl2[1:]:
        x = x['token']

        if '⦃' in x:
            input.append(x)
        else:
            if '⦃' in input[-1]:
                input.append(x)
            else:
                input[-1] += x

    for x in input:
        x = x.replace('\n\n', '\n').replace('\n', '※')
        if '.' in x:
            x = x.split('. ')[1]
        if r := re.search('⦃(.*?)⦄', x):
            y = r.group(1)
            x = re.sub('⦃(.*?)⦄', '', x)
            if x[0] in '\'“”"‘’「」『』':
                x = x[1:-1]
        else:
            y = '旁白'

        while r := re.match('(.*?[。；！？※…]+)', x):
            if re.search('[\u4e00-\u9fff]', r.group(1)):
                out.append(f'{y}|{r.group(1)}')
            else:
                out[-1] += r.group(1)
            x = x.replace(r.group(1), '', 1)
        if len(x) > 0 and re.search('[\u4e00-\u9fff]', x):
            out.append(f'{y}|{x}')

    out2 = []
    for x in out:
        y, x = x.split('|')
        while len(x) > 80:
            if r := re.match('(.{1,60}[，、—]+)', x):
                out2.append(f'{y}|{r.group(1)}')
                x = x.replace(r.group(1), '', 1)
            else:
                out2.append(f'{y}|{x[:60]}')
                x = x[60:]
        out2.append(f'{y}|{x}')
    try:
        start_idx = int(start_idx)
    except:
        start_idx = 1
    outt = '\n'.join([f'{pre}_{i+start_idx:04d}|{x.replace("※※","※")}' for i, x in enumerate(out2)])
    return outt


def process_cut_spon(x, pre, start_idx, y):
    # 。，！？、；：「」『』\'“”_"‘’⦃⦄《》（）…—\n
    o1, o2, o3 = process_text3(x)
    out = []
    x = o1.replace('\n\n', '\n').replace('\n', '※')
    while r := re.match('(.*?[。；！？※…]+)', x):
        if re.search('[\u4e00-\u9fff]', r.group(1)):
            out.append(f'{y}|{r.group(1)}')
        else:
            out[-1] += r.group(1)
        x = x.replace(r.group(1), '', 1)
    if len(x) > 0 and re.search('[\u4e00-\u9fff]', x):
        out.append(f'{y}|{x}')

    out2 = []
    for x in out:
        y, x = x.split('|')
        while len(x) > 80:
            if r := re.match('(.{1,60}[，、—]+)', x):
                out2.append(f'{y}|{r.group(1)}')
                x = x.replace(r.group(1), '', 1)
            else:
                out2.append(f'{y}|{x[:60]}')
                x = x[60:]
        out2.append(f'{y}|{x}')
    try:
        start_idx = int(start_idx)
    except:
        start_idx = 1
    outt = '\n'.join([f'{pre}{i+start_idx:04d}|{x.replace("※※","※")}' for i, x in enumerate(out2)])
    return o1, o2, o3, outt
