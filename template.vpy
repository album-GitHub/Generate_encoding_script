import vapoursynth as vs
#导入vapoursynth 并以vs命名
import sys
#导入sys
import havsfunc as haf
#导入havsfunc并以haf作为别名
import muvsfunc as muvf
#导入muvsfunc并以muvf作为别名
import CSMOD as cs
#导入CSMOD并以cs作为别名
import fvsfunc as fvf
#导入fvsfunc并以fvf作为别名

core = vs.core

#设定最大使用缓存（内存）
core.max_cache_size = 8000

#输入视频
source  = r'@video'

#使用LWLibavSource滤镜解析原视频
src = core.lsmas.LWLibavSource(source,threads=0)

#调整分辨率
#src=core.resize.Spline36(src, 1280, 720)

#重要！使用VSFilterMod把字幕压制至视频中，‘src = core.vsfm.TextSubMod’这段不能乱改
src = core.vsfm.TextSubMod(src,file="@ass")

#输出色深
#src = fvf.Depth(src, 10)

#输出
src.set_output()

