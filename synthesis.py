from preprocess import *
from gradio import update as gu
import gradio as gr
import os, shutil
import librosa
import numpy as np
import soundfile as sf
import random
random.seed()


def init_syn_path():
    random.seed()
    name = str(random.randint(1, 1e16))
    try:
        shutil.rmtree(f'./{name}/')
    except:
        pass
    os.makedirs(f'./{name}/', exist_ok=True)
    return f'./{name}/'


def play_result_audio(file, syn_path):
    if file:
        y, sr = librosa.load(os.path.join(f'{syn_path}/output', file + '.wav'), sr=None)
        return (sr, y)
    else:
        return None


def play_result_text(file, syn_result):
    if file:
        return syn_result[file]
    else:
        return None


def syn_dc(hl2, cut_tb1, cut_tb2, model_select, pause_sentence, pause_paragraph, opsyn, syn_result, syn_path):
    cut_tb = process_cut(hl2, cut_tb1, cut_tb2)
    if cut_tb.strip() == '请先执行对话判断！':
        gr.Error('请先执行对话判断（步骤1与2）！')
        return cut_tb, gu()
    else:
        cut_tbs = cut_tb.splitlines()
        os.makedirs(f'{syn_path}/tmp', exist_ok=True)
        os.makedirs(f'{syn_path}/output', exist_ok=True)
        syn_input = [x.split('|') for x in cut_tbs]

        ### 此处需补充语音合成部分的代码（因版权与保密问题无法公开），模型选项为model_select，输入为syn_input，每句话语音保存至'{syn_path}/tmp/{fn}.wav' ###

        first_fn = ''
        if '单句' in opsyn:
            for fn, yinse, text in [x.split('|') for x in cut_tbs]:
                first_fn = fn if first_fn == '' else first_fn
                shutil.copy(f'{syn_path}/tmp/{fn}.wav', f'{syn_path}/output/{fn}_{model_select}_{yinse}.wav')
                syn_result[f'{fn}_{model_select}_{yinse}'] = text

        if '篇章' in opsyn:
            ss = np.zeros(int(24000 * pause_sentence))
            sp = np.zeros(int(24000 * pause_paragraph))
            audios = []
            for fn, yinse, text in [x.split('|') for x in cut_tbs]:
                audio, _ = librosa.load(f'{syn_path}/tmp/{fn}.wav', sr=24000, mono=True)
                audios.append(audio)
                audios.append(sp if text[-1] == '※' else ss)
            final_audio = np.concatenate(audios[:-1])
            pianzhang_fn = f'{cut_tbs[0].split("|")[0]}-{fn.split("_")[-1]}_{model_select}'
            first_fn = pianzhang_fn
            sf.write(f'{syn_path}/output/{pianzhang_fn}.wav', final_audio, 24000)
            syn_result[f'{pianzhang_fn}'] = cut_tb

        ls = list(sorted(syn_result))
        return cut_tb, gu(choices=ls, value=first_fn), syn_result

def syn_spon(hl2, cut_tb1, cut_tb2, model_select, pause_sentence, pause_paragraph, opsyn, opsyn2, syn_result, syn_path, spk_audio_list):
    o1, o2, o3, cut_tb = process_cut_spon(hl2, cut_tb1, cut_tb2, spk_audio_list)

    cut_tbs = cut_tb.splitlines()
    os.makedirs(f'{syn_path}/tmp', exist_ok=True)
    os.makedirs(f'{syn_path}/output', exist_ok=True)
    syn_input = [x.split('|') for x in cut_tbs]

    ### 此处需补充语音合成部分的代码（因版权与保密问题无法公开），模型选项为model_select，输入为syn_input，每句话语音保存至'{syn_path}/tmp/{fn}.wav' ###

    first_fn = ''
    if '单句' in opsyn:
        for fn, yinse, text in [x.split('|') for x in cut_tbs]:
            first_fn = fn if first_fn == '' else first_fn
            shutil.copy(f'{syn_path}/tmp/{fn}.wav', f'{syn_path}/output/{fn}_{model_select}_{yinse}.wav')
            syn_result[f'{fn}_{model_select}_{yinse}'] = text

    if '篇章' in opsyn:
        ss = np.zeros(int(24000 * pause_sentence))
        sp = np.zeros(int(24000 * pause_paragraph))
        audios = []
        for fn, yinse, text in [x.split('|') for x in cut_tbs]:
            audio, _ = librosa.load(f'{syn_path}/tmp/{fn}.wav', sr=24000, mono=True)
            audios.append(audio)
            audios.append(sp if text[-1] == '※' else ss)
        final_audio = np.concatenate(audios[:-1])
        pianzhang_fn = f'{cut_tbs[0].split("|")[0]}-{fn.split("_")[-1]}_{model_select}'
        first_fn = pianzhang_fn
        sf.write(f'{syn_path}/output/{pianzhang_fn}.wav', final_audio, 24000)
        syn_result[f'{pianzhang_fn}'] = cut_tb

    ls = list(sorted(syn_result))
    return o1, o2, o3, cut_tb, gu(choices=ls, value=first_fn), syn_result
