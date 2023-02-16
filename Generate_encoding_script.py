import os
import re
import shutil
import sys
import ffmpeg
import subprocess
import configparser
from tkinter import filedialog

class Collect:
    def __init__(self):
        '''
        当前版本:v2.0.2
        完成时间:2023/2/16 19:39
        '''
        cf = configparser.ConfigParser()
        cf.read('config.ini', encoding='utf-8-sig')#, encoding='utf-8-sig'
        self.sections = cf.sections()
        self.x265 = cf.get("path", "x265_path")
        self.x264 = cf.get("path", "x264_path")
        self.vspipe = cf.get("path", "vspipe_path")
        self.ffmpeg_path = cf.get("path", "ffmpeg")
        self.MP4Box = cf.get("path", "MP4Box_path")
        self.mode = int(cf.get("mode", "mode"))
        self.extra_mode = int(cf.get("mode", "extra_mode"))
        self.cut_amount = int(cf.get("mode", "cut_amount"))
        self.extra_merge = cf.get("mode", "extra_merge")
        self.x264_switch = cf.get("mode", "x264")
        self.x265_switch = cf.get("mode", "x265")
        self.merge_sw = cf.get("mode", "merge")
        self.x264encoder = cf.get("encoder", "x264encoder")
        self.x265encoder = cf.get("encoder", "x265encoder")
        self.audio_bitrate = cf.get("encoder", "audio_bitrate")
        self.au_supp_sw = cf.get("mode", "au_supp_sw")   #音频压制开关
        #从配置文件获取参数

        self.video_dict = {}
        self.sub_dict = {}
        #音频字典
        self.audio_dict = {}
        #vpy文件字典
        self.vpy_dict = {}
        

        #获取脚本运行时所在目录
        self.py_path = os.path.dirname(os.path.abspath(__file__))

        #获得选择好的文件夹
        self.input_list = sys.argv
        if len(self.input_list) < 2:
            print('输入为空, 手动选择文件夹')
            self.folder = filedialog.askdirectory() 
        else:
            #暂只支持输入单个文件夹
            print('手动选择文件夹')
            self.folder = self.input_list[1]
        #把工作目录修改到指定目录
        os.chdir(self.folder)  

    def getpath(self, filepath):
        '''
        获取选中文件夹中包含的ass字幕与视频
        filepath:选中的文件夹
        获取文件夹内文件并提取出视频与字幕文件
        '''
        ass_file = []
        video_file = []
        #视频文件后缀名
        video = [
            '.mp4',
            '.mkv'
            ]
        sub = '.ass'
        for root,dirs,files in os.walk(filepath):
            for file in files:
                ys_file = os.path.join(root,file)
                file_name = os.path.basename(ys_file)
                #获取无尾缀文件名
                if os.path.splitext(file_name)[1] in video : # 如果文件是视频
                    video_file.append(os.path.normpath(ys_file))
                if os.path.splitext(file_name)[1] in sub : # 如果文件是视频
                    ass_file.append(os.path.normpath(ys_file))
        return video_file,ass_file

    def video_matching(self, video):
        '''
        返回对应集数的视频，字幕字典，字幕字典分为四个
        video:
        ass:

        '''
        #视频字典
        video_dict = {}
        
        for v in video:
            #获取文件名 不含文件夹名 如 test.txt
            videofile = os.path.basename(v)
            #只获取文件名
            match = re.search(r'E(\d{2})|\[(\d{2})\]|第 (\d{2}) 話|第 (\d{2}) 话|第(\d{2})話|第(\d{2})话', videofile, re.IGNORECASE)
            if match:
                episode =  next((group for group in match.groups() if group is not None), None)
                video_dict[episode] = v
            else:
                match = re.search(r"(?<!\d)(0[1-9]|[1-5][0-9])(?!\d)", videofile, re.IGNORECASE)
                if match:
                    print('match2',match)
                    episode =  next((group for group in match.groups() if group is not None), None)
                    video_dict[episode] = os.path.normpath(v)
                    #以 集数：文件完整路径 方式写入字典
                else:
                    print('视频集数匹配失败')
        return video_dict

    def ass_matching(self, ass):
        '''
        识别字幕文件集数与语言
        ass:字幕文件
        '''
        chs_dict = {}
        cht_dict = {}
        chsjp_dict = {}
        chtjp_dict = {}

        sub_dict = {}
        for a in ass:
            #获取文件名 不含文件夹名 如 test.txt
            assfile = os.path.basename(a)
            #只获取文件名
            match = re.search(r'E(\d{2})|\[(\d{2})\]|第 (\d{2}) 話', assfile, re.IGNORECASE)
            if match:
                episode =  next((group for group in match.groups() if group is not None), None)
            if not match:
                match = re.search(r"(?<!\d)(0[1-9]|[1-5][0-9])(?!\d)", assfile, re.IGNORECASE)
                if match:
                    episode =  next((group for group in match.groups() if group is not None), None)
            else:
                print('视频集数匹配失败')
            #判断字幕语言
            asstype = self.assname_cut(assfile)
            #根据语言添加到对应语言词典去
            if asstype == 1:
                chs_dict[episode] = os.path.normpath(a)
            elif asstype == 2: 
                cht_dict[episode] = os.path.normpath(a)
            elif asstype == 3:
                chsjp_dict[episode] = os.path.normpath(a)
            elif asstype == 4:
                chtjp_dict[episode] = os.path.normpath(a)
            elif asstype == 0:
                print('未识别出字幕语言')
                return 0
        sub_dict['chs'] = chs_dict
        sub_dict['cht'] = cht_dict
        sub_dict['chs_jp'] = chsjp_dict
        sub_dict['cht_jp'] = chtjp_dict
        return sub_dict

    def assname_cut(self, assfile):
        #根据字幕文件名判断字幕类型,返回0为异常，返回1为简体，返回2繁体，返回3简日
        
        #print('输入字幕为:',str(assfile))
        chsname = ['chs','简体']
        chtname = ['cht','繁体']
        chsjpname = ['chs_jp','chs-jp','chs jp','简日']
        chtjpname = ['cht_jp','cht-jp','cht jp','繁日']
        ass = []
        chs_y = 0
        cht_y = 0
        chsjp_y = 0
        chtjp_y = 0
        
        pattern_chs = '|'.join(chsname)
        pattern_cht = '|'.join(chtname)
        pattern_chsjp = '|'.join(chsjpname)
        pattern_chtjp = '|'.join(chtjpname)

        if re.search(pattern_chs, assfile, re.IGNORECASE):
            chs_y = 1
        if re.search(pattern_cht, assfile, re.IGNORECASE):
            cht_y = 1
        if re.search(pattern_chsjp, assfile, re.IGNORECASE):
            chsjp_y = 1
        if re.search(pattern_chtjp, assfile, re.IGNORECASE):
            chtjp_y = 1
        if chs_y+cht_y+chsjp_y+chtjp_y > 2 or chs_y+cht_y+chsjp_y+chtjp_y < 1:
            #检测是否文件名错误或匹配失败
            print('无法识别字幕类型，请检查字幕命名，文件为：', assfile,'各结果为：',chs_y,' ',cht_y,' ',chsjp_y,chtjp_y,' ass:',ass)
            sys.exit()
        if chs_y > 0 :
            print('结果为简体，文件为：',assfile)
            return 1
        elif cht_y > 0 :
            print('结果为繁体，文件为：',assfile)
            return 2
        elif chsjp_y > 0 :
            print('结果为简日，文件为：',assfile)
            return 3
        elif chtjp_y > 0 :
            print('结果为繁日，文件为：',assfile)
            return 4


    def audio_separation(self, video):
        audio_type =''
        video_info = ffmpeg.probe(video)
        #print('输入视频ffmpeg信息：',video_info)
        for items in video_info['streams']:
            try:
                if items['codec_type'] == 'audio':
                    audio_type = items['codec_name']
                    #返回音频编码格式
                    audio_track = items['index']
                    #返回音频轨号
                    return audio_type, audio_track
                else:
                    pass
            except:
                #找不到音轨，返回0
                print('未找到音轨')
                return False
        if audio_type == '':
            #找不到音轨，返回0
            return False

    def audio_extract(self, video, audio_inf):
        """
        输入视频:   vido_file
        音频信息:   audio_inf   #输入为数组
        音频轨道:   audio_track
        """
        
        pipe_in = 1 #判断用
        p = 1
        #获取文件所在文件夹 如 d:/test
        video_dir = os.path.dirname(video)
        #获取文件名 不含文件夹名 如 test.txt
        videos = os.path.basename(video)
        #获取文件名字 不含后缀 如 test
        vido_name = os.path.splitext(videos)[0]
        #拼接完整音频名称，包含后缀
        audio_name = str(video_dir)+'/'+str(vido_name)+'.'+str(audio_inf[0])
        command_in = ('"'+str(self.ffmpeg_path)+'" -i '+'"'+video+'"'+' -map 0:'+str(audio_inf[1])+' -vn -acodec copy '+'"'+audio_name+'"')
        #检测文件是否已经存在，存在则直接跳过提取
        if os.path.exists(audio_name):
            #文件已存在，跳过提取
            p = 0
            pipe_in = 1
        else:
            #直接传递给命令行执行
            print('command_in',command_in)
            pipe = subprocess.run(command_in)
            pipe_in = pipe.returncode
            
            
        if  pipe_in== 0 or p == 0:
            if p == 0:
                print('音频已存在，文件为:',audio_name)
            else:
                print('音频提取成功,文件为:',audio_name)
            audio_file = audio_name
            if audio_inf[0] != 'aac' and self.au_supp_sw == 'True':
                #如果音频文件类型不为aac且音频压制开关为True则传递至音频压制
                audio_file = self.audio_compress(audio_name)
                return os.path.normpath(audio_file)
            else:
                return os.path.normpath(audio_file)
        else:
            print('音频提取失败')


    def audio_compress(self, audio_file):
        '''
        音频压制模块
        输入音频:   audio_file
        音频比特率: audio_bit_rate
        音频采样率: audio_sample_rate
        return:  压制完的音频
        '''
        #变量预赋值
        passs = 0
        #通过ffmpeg获取所有信息
        audio_info = ffmpeg.probe(audio_file)
        #print('audio_info',audio_info)
        #获取音频信息
        for inf in audio_info['streams']:
            #记得加获取不到码率自动填写共功能
            audio_bit_rate = inf['bit_rate']
            #返回音频码率 准确数值需除以一千
            audio_sample_rate = inf['sample_rate']
            #返回音频采样率

        pipe_in = 1 #判断用
        #获取文件所在文件夹 如 d:/test
        dir = os.path.dirname(audio_file)
        #获取文件名字 不含后缀 如 test
        audioname = os.path.splitext(audio_file)[0]
        #分离文件后缀名前的路径
        audio_name = audioname +'.aac'
        #码率根据配置文件模式进行设置
        if self.audio_bitrate == 'auto':
            bitrate = audio_bit_rate
        else:
            bitrate = self.audio_bitrate
        parameter = ('"'+str(self.ffmpeg_path)+'" -y -i '+'"'+audio_file+'"'+' -vn -acodec aac -ac 2 -ab '+str(bitrate)+' -ar '+audio_sample_rate+' "'+str(audio_name)+'"')
        if os.path.exists(audio_name):
            #检测文件是否已经存在，存在则直接跳过压制
            passs = 0
            print('文件已存在，跳过压制:',os.path.normpath(audio_name))
            return str(audio_name)
        else:
            pipe_in = subprocess.run(parameter)
            #提交给命令行处理
        if pipe_in == 0 or passs == 0:
            print('压制成功:',os.path.normpath(audio_name))
            return os.path.normpath(audio_name)

    def coded_command(self, save_path, audio_path, vpy_path, encoder):
        '''
        压制代码生成
        ..._path：各类文件
        encoder：编码器模式，x264或x265
        '''
        if encoder == 'x264':
            x264_config = '"'+str(self.vspipe)+'"  -o 0 --y4m "'+str(vpy_path)+'" - | "'+str(self.x264)+'" '+str(self.x264encoder)+' --output "'+save_path+'.264" -'
            #合并mkv模块
            if self.merge_sw == 'True' and self.au_supp_sw == 'True':
                MP4Boxconfig = '"'+self.MP4Box+'" -add "'+save_path+'.264" -add "'+audio_path+ '" -new "'+ save_path +'-x264-muxed.mp4"'
                x264_config = x264_config + '\n' + MP4Boxconfig
            return x264_config
        elif encoder == 'x265':
            x265_config = '"'+str(self.vspipe)+'" --y4m "'+str(vpy_path)+'" - | "'+str(self.x265)+'" '+str(self.x265encoder)+' --output "'+save_path+'.HEVC" -'
            #合并mkv模块
            if self.merge_sw == 'True' and self.au_supp_sw == 'True':
                MP4Boxconfig = '"'+self.MP4Box+'" -add "'+save_path+'.HEVC" -add "'+audio_path+ '" -new "'+save_path+'-x265-muxed.mp4"'
                x265_config = x265_config + '\n' + MP4Boxconfig
            return x265_config
        
    def bat_save(self, save_path, encoder):
        '''
        save_path:bat文件保存路径
        encoder:压制代码
        '''
        if os.path.exists(save_path):
            #判断文件是否存在，已存在则退出
            print('文件已存在')
            return
        else:
            shutil.copy(self.py_path+'/encoder.bat', save_path)
            #复制模板文件并重命名
            
            file_data = ""
            with open(save_path, "r", encoding="utf-8") as f:
            #打开复制好的模板文件并修改
                for line in f:
                    if '@config' in line:
                    #遍历文件每一行并查找需替换的字符串
                        line = line.replace('@config',encoder)
                    file_data += line
            with open(save_path,"w",encoding="utf-8") as f:
                #修改完保存文件
                f.write(file_data)
            print('文件',save_path,'写入完毕')


    def bat_encoder(self, dict_all):
        """
        vpy:vpy文件完整路径
        save_path:生成的文件名称，无后缀
        audio:
        merge:合并mkv开关
        """
        #mode 0 各字幕文件生成独立压制bat
        if self.mode == 0:
            #循环输出各字幕列表
            for u in dict_all['sub'].keys():
                #如字典内为空则跳过
                if len(dict_all['sub'][u]) == 0:
                        continue
                #循环输出视频字典集数
                for v in dict_all['video']:
                    #获取vpy文件、视频文件不含含后缀名、音频文件
                    vpy_path = dict_all['vpy'][u][v]
                    save_path = str(os.path.splitext(dict_all['sub'][u][v])[0]) + '-' + str(u)
                    audio_path = dict_all['audio'][v]
                    #根据编码器设置生成编码命令，并保存至bat文件
                    if self.x264_switch == 'True':
                        x264_encoder = self.coded_command(save_path, audio_path, vpy_path,'x264')
                        self.bat_save(save_path+'-x264.bat',x264_encoder)
                    if self.x265_switch == 'True':
                        x265_encoder = self.coded_command(save_path, audio_path, vpy_path,'x265')
                        self.bat_save(save_path+'-x265.bat',x265_encoder)
        #mode 1 各编码器生成独立压制bat
        if self.mode == 1:
            #循环输出各字幕列表
            x264_encoder = ''
            x265_encoder = ''
            for u in dict_all['sub'].keys():
                #如字典内为空则跳过
                if len(dict_all['sub'][u]) == 0:
                        continue
                #循环输出视频字典集数
                
                for v in dict_all['video']:
                    #获取vpy文件、视频文件不含含后缀名、音频文件
                    vpy_path = dict_all['vpy'][u][v]
                    save_path = str(os.path.splitext(dict_all['sub'][u][v])[0]) + '-' + str(u)

                    audio_path = dict_all['audio'][v]
                    #根据编码器设置生成编码命令，并保存至bat文件
                    if self.x264_switch == 'True':
                        x264 = self.coded_command(save_path, audio_path, vpy_path,'x264')
                        x264_encoder = x264_encoder + '\n' + x264
                    if self.x265_switch == 'True':
                        x265 = self.coded_command(save_path, audio_path, vpy_path,'x265')
                        x265_encoder = x265_encoder + '\n' + x265
            if self.x264_switch == 'True':
                self.bat_save(str(os.path.dirname(dict_all['sub'][u][v])) + '/all-x264.bat',x264_encoder)
            if self.x265_switch == 'True':
                self.bat_save(str(os.path.dirname(dict_all['sub'][u][v])) + '/all-x265.bat',x265_encoder)
        if self.mode == 2:
            #循环输出视频字典集数
            for v in dict_all['video']:
                x264_encoder = ''
                x265_encoder = ''
                #循环输出各字幕列表
                for u in dict_all['sub'].keys():
                    #如字典内为空则跳过
                    if len(dict_all['sub'][u]) == 0:
                        break
                    #获取vpy文件、视频文件不含含后缀名、音频文件
                    vpy_path = dict_all['vpy'][u][v]
                    save_path = str(os.path.splitext(dict_all['video'][v])[0]) + '-' + str(u)
                    audio_path = dict_all['audio'][v]
                    #根据编码器设置生成编码命令，并保存至bat文件
                    if self.x264_switch == 'True':
                        x264 = self.coded_command(save_path, audio_path, vpy_path,'x264')
                        x264_encoder = x264_encoder + '\n' + x264
                    if self.x265_switch == 'True':
                        x265 = self.coded_command(save_path, audio_path, vpy_path,'x265')
                        x265_encoder = x265_encoder + '\n' + x265
                if self.x264_switch == 'True':
                    self.bat_save(save_path + '-x264.bat',x264_encoder)
                if self.x265_switch == 'True':
                    self.bat_save(save_path + '-x265.bat',x265_encoder)

        #mode 3 仅对视频进行压制
        if self.mode == 3:
            video_count = len(dict_all['video'])
            #视频计数用 单个bat文件写入后清零
            count = 0
            #总处理的数量
            count_all = 0
            #当前组数量
            count_set = 0
            #模式3、4压制额外选项的模式2时，等分bat数量小于视频数量则等分成视频数量值
            if video_count <= self.cut_amount:
                self.cut_amount = video_count
            #等分取整后的每份bat文件数量
            divide = video_count // self.cut_amount
            #依次输出视频文件
            
            x264_encoder = ''
            x265_encoder = ''
            for v in dict_all['video']:
                #去掉路径后缀名
                video_flie = str(os.path.splitext(v)[0])
                #依次输出音频文件
                for a in dict_all['audio']:
                    #去掉路径后缀名
                    audio_flie = str(os.path.splitext(a)[0])
                    #如果输出的音频文件名与视频名不符则退出当前for循环
                    if video_flie != audio_flie:
                        continue
                    #依次输出vpy文件
                    for p in dict_all['vpy']:
                        #去掉路径后缀名
                        vpy_flie = str(os.path.splitext(p)[0])
                        #如果三个去掉后缀名的文件名相等则继续
                        if video_flie == audio_flie == vpy_flie:
                            vpy_path = p
                            save_path = video_flie
                            audio_path = audio_flie
                            count = count + 1
                            count_all = count_all + 1
                            if self.x264_switch == 'True':
                                x264 = self.coded_command(save_path, audio_path, vpy_path,'x264')
                                x264_encoder = x264_encoder + '\n' + x264
                            if self.x265_switch == 'True':
                                x265 = self.coded_command(save_path, audio_path, vpy_path,'x265')
                                x265_encoder = x265_encoder + '\n' + x265
                            
                            if self.extra_mode == 0:
                                if self.x264_switch == 'True':
                                    self.bat_save(save_path + '-x264.bat',x264)
                                if self.x265_switch == 'True':
                                    self.bat_save(save_path + '-x265.bat',x265)
                                #释放临时存储
                                x264_encoder = ''
                                x265_encoder = ''
                            #模式2，等分模式
                            '''
                            以下逻辑为：循环了整除数量的次数时生成一次，当生成次数等于最终次数的倒数最后一次且视频为最后一个时生成最后一个bat文件
                            '''
                            if self.extra_mode == 2 and ((count == divide and count_set + 1 < self.cut_amount) or (count_set + 1 == self.cut_amount and count_all == video_count)):
                                count_set = count_set + 1
                                count = 0
                                if self.x264_switch == 'True' and self.x265_switch == 'True' and self.extra_merge == 'True':
                                    self.bat_save(f'{count_set}-all_encoder.bat',x264_encoder + '\n' + x265_encoder)
                                if self.x264_switch == 'True' and self.extra_merge != 'True':
                                    self.bat_save(f'{count_set}-x264.bat',x264_encoder)
                                if self.x265_switch == 'True' and self.extra_merge != 'True':
                                    self.bat_save(f'{count_set}-x265.bat',x265_encoder)
                                #释放临时存储
                                x264_encoder = ''
                                x265_encoder = ''
                        else:
                            continue
            if self.extra_mode == 1:

                if self.x264_switch == 'True':
                    self.bat_save(str(os.path.dirname(v)) + '/all-x264.bat',x264_encoder)
                if self.x265_switch == 'True':
                    self.bat_save(str(os.path.dirname(v)) + '/all-x265.bat',x265_encoder)
                x264_encoder = ''
                x265_encoder = ''
                        




    def audio_processing(self, video):
        
        #循环输出字典的键名
        if self.mode in [0 , 1 , 2]:
            audio_dict = {}
            for v in video.keys():
                #获取音频数据 0音频编码格式audio_type 1音频音轨号audio_track 2音频比特率audio_bit_rate 3音频码率audio_sample_rate
                audio_tyoe = self.audio_separation(video[v])
                if audio_tyoe == False:
                    print('该视频音频信息获取失败')
                    return
                #提取音频并压制，并写入音频列表字典
                audio_file = self.audio_extract(video[v],audio_tyoe)
                #写入集数对应音频文件字典
                audio_dict[v] = audio_file
                #print('audiodict',audiodict)
            if audio_dict != None:
                    return audio_dict
        if self.mode == 3:
            #只压制视频模式所以没有集数信息，返回的是列表
            audio_list = []
            for v in video:
                print('v',v)
                #获取音频数据 0音频编码格式audio_type 1音频音轨号audio_track 2音频比特率audio_bit_rate 3音频码率audio_sample_rate
                audio_tyoe = self.audio_separation(v)
                if audio_tyoe == False:
                    print('该视频音频信息获取失败')
                    return
                #提取音频并压制，并写入音频列表字典
                audio_file = self.audio_extract(v,audio_tyoe)
                #写入集数对应音频文件列表
                audio_list.append(audio_file)
                #print('audiodict',audiodict)
            if audio_list != None:
                    return audio_list
    def template_rec(self, video, ass):
        #复制模板文件并修改
        #print(video,'\n',ass)
        if self.mode in [0 , 1 , 2 , 4]:
            #字幕压制模式
            t_path = ass
        elif self.mode == 3:
            #仅视频压制模式
            t_path = video
        #获取文件名 不含文件夹名 如 test.txt
        name = os.path.basename(t_path)
        #获取文件名字 不含后缀 如 test
        file_name = os.path.splitext(name)[0]
        #获取文件所在文件夹 如 d:/test
        file_dir = os.path.dirname(t_path)
        #得到vpy文件完整路径
        vpy_path = file_dir +'/' + file_name + '.vpy'
        print('vpy_path',vpy_path)
        if os.path.exists(vpy_path):
        #判断文件是否存在，已存在则退出
            print('vpy文件已存在:',os.path.normpath(vpy_path))
            return os.path.normpath(vpy_path)
        else:
            shutil.copy(self.py_path+'/template.vpy', vpy_path)
            #复制模板文件并重命名
            file_data = ""
            with open(vpy_path, "r", encoding="utf-8") as f:
            #打开复制好的模板文件并修改
                for line in f:
                    if '@video' in line :
                    #遍历文件每一行并查找需替换的字符串 
                        line = line.replace('@video',str(video))
                    #字幕文件写入
                    if '@ass' in line and self.mode in [0 , 1 , 2 , 4]:
                        line = line.replace('@ass',str(ass))
                    #单视频压制则注释掉字幕压制一行
                    if 'src = core.vsfm.TextSubMod' in line and self.mode == 3:
                        line = line.replace('src = core.vsfm.TextSubMod','#src = core.vsfm.TextSubMod)')
                    file_data += line
            with open(vpy_path,"w",encoding="utf-8") as f:
                #修改完保存文件
                f.write(file_data)
                print('保存vpy文件：',os.path.normpath(vpy_path))
                return os.path.normpath(vpy_path)
        
    def template_advance(self, dict_all):
        #根据模式生成vpy文件
        dict_vpy = {}
        if self.mode in [0 , 1 , 2 , 4]:
            #循环输出每个字幕字典
            for u in dict_all['sub'].keys():
                vpy_path = {}
                #如字典内为空则跳过
                if len(dict_all['sub'][u]) == 0:
                        continue
                #循环输出视频字典内的集数
                for v in dict_all['video']:
                    #传递视频与字幕给vpy生成模块，并把传回的vpy文件名存入临时字典
                    vpy_path[v] = self.template_rec(dict_all['video'][v],dict_all['sub'][u][v])
                if vpy_path != None:
                    #不为空则把临时字典按字幕语言存入最终输出的字典
                    dict_vpy[u] = vpy_path
            return dict_vpy
        elif self.mode == 3:
            vpy_list = []
            for v in dict_all['video']:
                    #传递视频与字幕给vpy生成模块，并把传回的vpy文件名存入临时字典
                path = self.template_rec(v,None)
                if path != None:
                    #不为空则把vpy文件加入列表
                     vpy_list.append(path)
            return vpy_list


    def runs(self):
        if self.mode in [0 , 1 , 2]:
            dict_all = {}
            #返回 视频与字幕列表,[0]为视频字典，[1]为字幕字典
            file_list=self.getpath(self.folder)
            #返回 集数对应的视频字典
            self.video_dict = self.video_matching(file_list[0])
            dict_all['video'] = self.video_dict
            
            #返回 集数对应的字幕字典
            self.sub_dict = self.ass_matching(file_list[1])
            dict_all['sub'] = self.sub_dict
            #返回 集数对应音频文件字典
            self.audio_dict = self.audio_processing(self.video_dict)
            dict_all['audio'] = self.audio_dict
            
            #复制模板文件并修改，输入为视频字典、字幕字典
            self.vpy_dict = self.template_advance(dict_all)
            dict_all['vpy'] = self.vpy_dict
            #生成压制bat
            self.bat_encoder(dict_all)
        elif self.mode == 3:
            dict_all = {}
            #返回 视频与字幕列表,[0]为视频字典
            file_list=self.getpath(self.folder)
            dict_all['video'] = file_list[0]
            #返回vpy文件列表
            vpy_list = self.template_advance(dict_all)
            dict_all['vpy'] = vpy_list
            #返回 音频文件列表
            audio_list = self.audio_processing(file_list[0])
            dict_all['audio'] = audio_list

            self.bat_encoder(dict_all)
        
        sys.exit()
if __name__ == '__main__':
    mySpider = Collect()
    mySpider.runs()


