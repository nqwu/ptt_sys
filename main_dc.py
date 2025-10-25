import gradio as gr
from gradio import update as gu
from preprocess import *
from synthesis import *
import os, shutil
import librosa

REF_DICT = "dc_ref"

def list_ref_files(directory=REF_DICT):
    os.makedirs(directory, exist_ok=True)
    return list(sorted([f[:-4] for f in os.listdir(directory) if f.endswith(".wav")]))


def play_audio(file):
    if file:
        y, sr = librosa.load(os.path.join(REF_DICT, file + '.wav'), sr=None)
        return (sr, y)
    else:
        return None


def upload_audio(files):
    if files is None:
        gr.Warning("请先上传文件！")
        return gu(), gu()
    else:
        for file in files:
            shutil.copy(file, os.path.join(REF_DICT, os.path.basename(file)))
        gr.Info("上传成功！")
        ref_files = list_ref_files()
        return None, gu(choices=ref_files), gu(choices=ref_files)


def split_text(text):
    """Dummy text splitting function."""
    return text.split(".")


def delete_audio(selected_files):
    if not selected_files:
        gr.Warning("请选择要删除的音频！")
        return gu()

    for file in selected_files:
        file_path = os.path.join(REF_DICT, file + '.wav')
        if os.path.exists(file_path):
            os.remove(file_path)

    gr.Info("删除成功！")
    ref_files = list_ref_files()
    return gu(value=ref_files[0] if ref_files else None, choices=ref_files), gu(value=[], choices=ref_files)


def show_delete_options():
    if ref_files := list_ref_files():
        return gu(visible=False), gu(choices=ref_files), gu(visible=True)
    else:
        gr.Warning("参考语音库里没有文件！")
        return gu(), gu(), gu()


DEFTEXT = '''
    “在那红木箱子之中，共有63粒蜡丸，其中各包着一张字条，上书着从1至63此类数字，”众弟子忽地一阵喧哗，苍松道人不去理会，又道：“在抽签完成之后，即以数字为准进行比试。诸位明白了么?”
    站在堂下的“青云门”众弟子沉默了一会，忽然有人大声道：“请问苍松师叔，明明有64人，怎地却只有63粒蜡丸？”
'''

with gr.Blocks() as app:
    syn_result = gr.State({})
    syn_path = gr.State('')
    hl2_choices = gr.State([])

    app.load(fn=init_syn_path, inputs=None, outputs=[syn_path])
    gr.Markdown("## 篇章语音合成原型系统")
    with gr.Column():
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Accordion("步骤1 文本输入与预处理"):
                    text_input = gr.Textbox(
                        DEFTEXT,
                        lines=6,
                        placeholder='注意：输入文本不支持英文。对话部分推荐用使用标准的全角中文“”符号框起来，请勿将引号嵌套使用。】\n你可以直接粘贴篇章文本到此处，并使用下方按钮进行预处理。',
                        label='篇章纯文本输入',
                    )

                    hl1 = gr.HighlightedText(
                        [[' ', None]],
                        label='高亮窗口',
                        combine_adjacent=True,
                        show_legend=True,
                        visible=False,
                        color_map={"添加部分": "green", "删除部分": "red", "需检查修改": "yellow"},
                        interactive=False,
                    )
                    log_output = gr.Textbox(label='处理日志', interactive=False)

                    process_button1 = gr.Button("步骤1.1 预处理:数字文本标准化")
                    process_button2 = gr.Button("步骤1.2 预处理:特殊符号处理")
                    process_button3 = gr.Button("步骤1.3 预处理:检查括号与引号")
                    op3 = gr.CheckboxGroup(value=['删除括号内的文本'], choices=['删除括号内的文本', '引号内的内容允许换行'], show_label=False)

            with gr.Column(scale=2):

                with gr.Accordion("步骤2 对话判断与音色设置"):
                    with gr.Row():
                        with gr.Column():
                            with gr.Accordion("步骤2.1 对话判断"):
                                with gr.Accordion("对话判断选项", open=False):
                                    op41 = gr.CheckboxGroup(
                                        value=['“...”', '「...」', '说：...', '道：...'],
                                        label='满足以下形式之一的文本进入候选',
                                        choices=['“...”', '「...」', '"..."', '‘...’', '『...』', '\'...\'', '说：...', '道：...'],
                                        interactive=True,
                                    )
                                    op421 = gr.CheckboxGroup(value=['候选内部以如下标点符号之一结尾：'], choices=['候选内部以如下标点符号之一结尾：'], label='满足以下条件之一的候选判断成对话')
                                    tb421 = gr.Textbox('：，。；？！…—', show_label=False, interactive=True)
                                    op422 = gr.CheckboxGroup(value=['候选内部含有如下标点符号之一：'], choices=['候选内部含有如下标点符号之一：'], show_label=False)
                                    tb422 = gr.Textbox('：，。；？！…—', show_label=False, interactive=True)
                                    op423 = gr.CheckboxGroup(value=['候选部分的前面是以下标点符号之一：'], choices=['候选部分的前面是以下标点符号之一：'], show_label=False)
                                    tb423 = gr.Textbox('：', show_label=False, interactive=True)
                                    op424 = gr.CheckboxGroup(value=[], choices=['候选部分在段首'], show_label=False, interactive=True)
                                process_button4 = gr.Button("步骤2.1 对话判断")

                            hl2 = gr.HighlightedText(
                                label='对话判断结果',
                                combine_adjacent=True,
                                show_legend=True,
                                color_map={'候选但不是对话': "red", "对话（未选中）": "green", "对话（选中）": "blue"},
                                interactive=False,
                            )

                            with gr.Accordion("步骤2.2 音色设置"):
                                hl2_cb = gr.CheckboxGroup(label='对话多选窗口', interactive=True)
                                hl2_select_all_button = gr.Button("全选")
                                hl2_deselect_all_button = gr.Button("全不选")
                                hl2_bt1 = gr.Button('步骤2.2 设置选中句子为右侧参考音色')

                        with gr.Column():
                            with gr.Accordion("参考语音浏览与管理", open=True):
                                ref_files = list_ref_files()
                                ref_audio_list = gr.Radio(value=ref_files[0], choices=ref_files, show_label=False, interactive=True)
                                audio_player = gr.Audio(value=play_audio(ref_files[0]) if ref_files else None, label="参考语音浏览")
                                ref_audio_list.change(play_audio, inputs=ref_audio_list, outputs=audio_player)

                                with gr.Accordion("批量删除参考语音", open=False):
                                    with gr.Column(scale=3):
                                        delete_audio_list = gr.CheckboxGroup(ref_files, label="选择要删除的语音")
                                    with gr.Column(scale=1):
                                        select_all_button = gr.Button("全选")
                                        deselect_all_button = gr.Button("全不选")
                                        confirm_delete_button = gr.Button("确认删除")

                                    select_all_button.click(lambda: list_ref_files(), outputs=delete_audio_list)
                                    deselect_all_button.click(lambda: [], outputs=delete_audio_list)
                                    confirm_delete_button.click(delete_audio, inputs=delete_audio_list, outputs=[ref_audio_list, delete_audio_list])

                                with gr.Accordion("批量上传参考语音", open=False):
                                    upload = gr.File(file_types=[".wav"], file_count="multiple", label="上传参考语音")
                                    upload_button = gr.Button("将以上参考语音加入参考语音库")
                                    upload_button.click(upload_audio, inputs=upload, outputs=[upload, ref_audio_list, delete_audio_list])

                            process_button1.click(process_text1, inputs=text_input, outputs=[text_input, log_output, hl1])
                            process_button2.click(process_text2, inputs=text_input, outputs=[text_input, log_output, hl1])
                            process_button3.click(process_text3, inputs=[text_input, op3], outputs=[text_input, log_output, hl1])
                            process_button4.click(
                                process_text4,
                                inputs=[text_input, op3, op41, op421, tb421, op422, tb422, op423, tb423, op424, hl2_choices],
                                outputs=[text_input, log_output, hl1, hl2, hl2_cb, hl2_choices],
                            )
                            process_button4.click(lambda: [], outputs=hl2_cb)
                            hl2_select_all_button.click(lambda x: x, inputs=hl2_choices, outputs=hl2_cb)
                            hl2_deselect_all_button.click(lambda: [], outputs=hl2_cb)
                            hl2_cb.change(process_text4_change, inputs=[hl2_cb, hl2, hl2_choices], outputs=hl2)
                            hl2_bt1.click(process_text4_voice, inputs=[ref_audio_list, text_input, hl2, hl2_cb, hl2_choices], outputs=[text_input, hl2, hl2_cb, hl2_choices])
                            hl2_bt1.click(lambda: [], outputs=hl2_cb)

        with gr.Row():
            with gr.Accordion("步骤3 执行分句与编号"):
                cut_tb1 = gr.Textbox(value='合成语音', label='编号前缀')
                cut_tb2 = gr.Textbox(value='1', label='编号起始项')
                cut_bt = gr.Button('步骤3 执行分句与编号')
                cut_tb = gr.Textbox(label='分句结果[文件名|音色|文本]', interactive=False)
                cut_bt.click(process_cut, inputs=[hl2, cut_tb1, cut_tb2], outputs=[cut_tb])

            with gr.Accordion("步骤4 语音合成"):
                model_select = gr.Dropdown(["所提方法", "基线VITS2（仅单句合成）", "基线StyleTTS（仅单句合成）"], label="模型选择", interactive=True)
                pause_sentence = gr.Slider(0, 1, 0.5, step=0.1, label="句间停顿 (秒)", interactive=True)
                pause_paragraph = gr.Slider(0, 3, 1.5, step=0.1, label="段落间停顿 (秒)", interactive=True)
                opsyn = gr.Radio(value='输出篇章', choices=['输出篇章', '输出单句', '输出篇章与单句'], interactive=True, show_label=False)

                synth_button = gr.Button("步骤4 执行语音合成")

            with gr.Accordion("结果浏览", open=True):
                result_select = gr.Dropdown([], label="合成结果语音", interactive=True)
                result_text = gr.Textbox(label='原始文本', interactive=False)
                result_audio_player = gr.Audio(value=None, label="合成语音浏览", interactive=False)
                result_download_button = gr.Button("批量下载合成结果")
                synth_button.click(syn_dc, inputs=[hl2, cut_tb1, cut_tb2, model_select,  pause_sentence, pause_paragraph, opsyn, syn_result, syn_path], outputs=[cut_tb, result_select, syn_result])
                result_select.change(play_result_audio, inputs=[result_select,syn_path], outputs=result_audio_player)
                result_select.change(play_result_text, inputs=[result_select, syn_result], outputs=result_text)


app.launch(server_name='0.0.0.0', server_port=13506, share=False, debug=False, auth=None)
