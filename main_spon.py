import gradio as gr
from gradio import update as gu
from preprocess import *
from synthesis import *
import os
import librosa


def list_spk_files():
    return list(sorted([f[:-4] for f in os.listdir('spon_spk') if f.endswith('.wav')]))


REF_LIST = list(sorted([f[:-4].split('#') + [f] for f in os.listdir('spon_ref') if f.endswith('.wav')]))
REF_DICT = {x[0]: x[1:] for x in REF_LIST}


def list_ref_files(label='笑声', gen=['男性', '女性'], age=['青年', '中年']):
    xs = [x for x in REF_DICT if x.startswith(label)]
    xs = [x for x in xs if any([g in x for g in gen]) and any([a in x for a in age])]
    return xs


def list_ref_files_change(label, gen, age):
    ls = list_ref_files(label, gen, age)
    return gu(value=ls[0] if ls else None, choices=ls)


def play_text_ref(file):
    return REF_DICT[file][-3] if file else None


def play_audio_ref(file):
    if file:
        y, sr = librosa.load(os.path.join('spon_ref', REF_DICT[file][-1]), sr=None)
        return (sr, y)
    else:
        return None
    
def play_audio_ref2(file):
    if file:
        y, sr = librosa.load(os.path.join('spon_ref', REF_DICT[file][-1]), sr=None)
        return (sr, y[int(REF_DICT[file][0]):int(REF_DICT[file][1])])
    else:
        return None

def play_audio_spk(file):
    y, sr = librosa.load(os.path.join('spon_spk', file + '.wav'), sr=None)
    return (sr, y)

def play_sample_spk():
    y, sr = librosa.load(os.path.join('sample.wav'), sr=None)
    return (sr, y)


def split_text(text):
    """Dummy text splitting function."""
    return text.split(".")


def insert_js(x):
    return """
() => {
    const textarea = document.querySelector("#my_textbox textarea");
    if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const value = textarea.value;
        const insertText = "（）";
        textarea.value = value.slice(0, start) + insertText + value.slice(end);
        textarea.focus();
        textarea.selectionStart = textarea.selectionEnd = start + insertText.length;
        const inputEvent = new Event("input", { bubbles: true });
        textarea.dispatchEvent(inputEvent);
    }
}
""".replace(
        '（）', f'（{x}）'
    )


SPON_LABELS = ['吸气', '间断', '拖音', '口误', '沉默', '吸鼻', '深吸', '笑声']
DEFTEXT = '''恩主要原因可能主要是这几点吧,第1是父母都是我是出生于教师之家（吸气)。父（间断）恩父亲呢是（口误）恩英语教师（吸气）。母亲恩（笑声）母亲也是（间段）也是教师吧,所以（吸气）从小受到他们的[间断]影响熏陶。'''

with gr.Blocks() as app:
    syn_result = gr.State({})
    syn_path = gr.State('')
    app.load(fn=init_syn_path, inputs=None, outputs=[syn_path])
    gr.Markdown("## 口语化语音合成原型系统")

    with gr.Row():
        with gr.Column():
            with gr.Accordion("步骤1 文本输入与预处理"):
                text_input = gr.Textbox(
                    DEFTEXT,
                    lines=4,
                    elem_id="my_textbox",
                    placeholder='注意：输入文本不支持英文。口语现象请用圆形括号（）括起来。\n你可以直接粘贴篇章文本到此处，并使用下方按钮进行预处理。',
                    label='文本输入',
                )
                hl1 = gr.HighlightedText(
                    [[' ', None]], label='高亮窗口', combine_adjacent=True, show_legend=True, visible=False, color_map={"添加部分": "green", "删除部分": "red", "需检查修改": "yellow"}, interactive=False
                )
                log_output = gr.Textbox(label='处理日志', interactive=False)

                process_button1 = gr.Button("步骤1.1 预处理:数字文本标准化")
                process_button2 = gr.Button("步骤1.2 预处理:特殊符号处理")
                process_button3 = gr.Button("步骤1.3 预处理:括号与引号规整")
                
            with gr.Accordion("步骤2 自动口语化"):
                process_button5 = gr.Button("步骤2.1 文本口语化转换（可选）")
                process_button4 = gr.Button("步骤2.2 口语现象预测（可选）")
                process_button45 = gr.Button("步骤2.1 + 步骤2.2")
                with gr.Accordion("步骤2.2 口语概率系数设置", open=False):
                    p_labels = [gr.Slider(0, 2, 1, step=0.05, label=f"预测（{x}）的概率系数", interactive=True) for x in SPON_LABELS]

                ### 此处需补充文本口语化转换与口语现象预测的模块（因版权与保密问题无法公开） ###

        with gr.Accordion("步骤3 手动插入口语现象（可选）"):

            with gr.Accordion("步骤3.1 在光标位置插入口语现象（可选）"):
                with gr.Row():
                    insert_bts = []
                    for x in SPON_LABELS:
                        insert_bts.append(gr.Button(f"{x}", min_width=80,size='md'))
                        insert_bts[-1].click(None, js=insert_js(x))
                        
            with gr.Accordion("步骤3.2 在光标位置插入参考口语现象（可选）"):
                ref_op_l = gr.Radio(value='笑声', choices=['笑声', '深吸', '吸鼻'], label='参考口语现象类型')
                with gr.Row():
                    ref_op_a = gr.CheckboxGroup(value=['青年', '中年'], choices=['青年', '中年'], label='年龄筛选')
                    ref_op_g = gr.CheckboxGroup(value=['男性', '女性'], choices=['男性', '女性'], label='性别筛选')
                ref_files = list_ref_files()

                ref_audio_list = gr.Dropdown(value=ref_files[0], choices=ref_files, show_label=False, interactive=True)
                ref_bt = gr.Button(f"插入该参考口语现象")
                ref_text = gr.Text(value=play_text_ref(ref_files[0]), show_label=False)

                ref_audio_player = gr.Audio(value=play_audio_ref(ref_files[0]) if ref_files else None, label="完整参考语音浏览")
                ref_audio_player2 = gr.Audio(value=play_audio_ref2(ref_files[0]) if ref_files else None, label="参考语音中的口语现象浏览")

                ref_audio_list.change(play_audio_ref, inputs=ref_audio_list, outputs=[ref_audio_player])
                ref_audio_list.change(play_audio_ref2, inputs=ref_audio_list, outputs=[ref_audio_player2])
                ref_audio_list.change(play_text_ref, inputs=ref_audio_list, outputs=ref_text)
                ref_op_l.change(list_ref_files_change, inputs=[ref_op_l, ref_op_a, ref_op_g], outputs=ref_audio_list)
                ref_op_a.change(list_ref_files_change, inputs=[ref_op_l, ref_op_a, ref_op_g], outputs=ref_audio_list)
                ref_op_g.change(list_ref_files_change, inputs=[ref_op_l, ref_op_a, ref_op_g], outputs=ref_audio_list)
                
                ref_bt.click(
                    None,
                    inputs=[ref_audio_list],
                    js="""
                            (label) => {
                                const textarea = document.querySelector("#my_textbox textarea");
                                if (textarea) {
                                    const start = textarea.selectionStart;
                                    const end = textarea.selectionEnd;
                                    const value = textarea.value;
                                    const insertText = label;
                                    textarea.value = value.slice(0, start) + "（" + insertText + "）" + value.slice(end);
                                    textarea.focus();
                                    textarea.selectionStart = textarea.selectionEnd = start + insertText.length + 2;
                                    const event = new Event("input", { bubbles: true });
                                    textarea.dispatchEvent(event);
                                }
                            }
                            """,
                )
                
        with gr.Column():
            with gr.Accordion("步骤4 选择说话人音色"):
                ref_files = list_spk_files()
                spk_audio_list = gr.Dropdown(value=ref_files[0], choices=ref_files, show_label=False, interactive=True)
                spk_audio_player = gr.Audio(value=play_audio_spk(ref_files[0]) if ref_files else None, label="说话人音色浏览")
                spk_audio_list.change(play_audio_spk, inputs=spk_audio_list, outputs=spk_audio_player)
        

            with gr.Accordion("步骤5 执行分句与编号"):
                cut_tb1 = gr.Textbox(value='合成语音',label='编号前缀')
                cut_tb2 = gr.Textbox(value='1', label='编号起始项')
                cut_bt = gr.Button('步骤5 执行分句与编号')
                cut_tb = gr.Textbox(label='分句结果[文件名|音色|文本]', interactive=False)

        with gr.Column():
            with gr.Accordion("步骤6 语音合成"):
                model_select = gr.Dropdown(["口语化VITS2", "基线VITS2"], label="模型选择", interactive=True)
                pause_sentence = gr.Slider(0, 1, 0.5, step=0.1, label="句间停顿 (秒)", interactive=True)
                pause_paragraph = gr.Slider(0, 3, 1.5, step=0.1, label="段落间停顿 (秒)", interactive=True)
                opsyn = gr.Radio(value='输出篇章与单句', choices=['输出篇章', '输出单句', '输出篇章与单句'], interactive=True, show_label=False)
                opsyn2 = gr.Radio(value='稀有现象随机选择参考', choices=['稀有现象随机选择参考', '稀有现象直接合成'], interactive=True, show_label=False)
                synth_button = gr.Button("步骤6 执行语音合成")

            with gr.Accordion("结果浏览", open=True):
                result_select = gr.Dropdown([], label="合成结果语音", interactive=True)
                result_text = gr.Textbox(label='原始文本', interactive=False)
                result_audio_player = gr.Audio(value=None, label="合成语音浏览",interactive=False)
                result_download_button = gr.Button("批量下载合成结果")
                synth_button.click(syn_spon, inputs=[text_input, cut_tb1, cut_tb2, model_select, pause_sentence, pause_paragraph, opsyn,opsyn2, syn_result, syn_path, spk_audio_list], outputs=[text_input, log_output, hl1, cut_tb, result_select, syn_result])
                result_select.change(play_result_audio, inputs=[result_select, syn_path], outputs=result_audio_player)
                result_select.change(play_result_text, inputs=[result_select, syn_result], outputs=result_text)

        process_button1.click(process_text1, inputs=text_input, outputs=[text_input, log_output, hl1])
        process_button2.click(process_text2, inputs=text_input, outputs=[text_input, log_output, hl1])
        process_button3.click(process_text3, inputs=text_input, outputs=[text_input, log_output, hl1])
        cut_bt.click(process_cut_spon, inputs=[text_input, cut_tb1, cut_tb2, spk_audio_list], outputs=[text_input, log_output, hl1, cut_tb])

app.launch(server_name='0.0.0.0', server_port=13507, share=False, debug=False, auth=None)
