# -*- coding: utf-8 -*-
"""把 10 页演示内容生成真正的 .pptx（16:9），供「求职综合展示」提交。"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

PRIMARY = RGBColor(0x1E, 0x40, 0xAF)
ACCENT = RGBColor(0x05, 0x96, 0x69)
INK = RGBColor(0x0F, 0x17, 0x2A)
MUTED = RGBColor(0x64, 0x74, 0x8B)
LIGHT = RGBColor(0xEE, 0xF2, 0xF7)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

SW, SH = prs.slide_width, prs.slide_height


def add_title(slide, text):
    box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.1), Inches(0.9))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = PRIMARY
    line = slide.shapes.add_shape(1, Inches(0.62), Inches(1.15), Inches(2.2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT
    line.line.fill.background()
    return slide


def add_body(slide, items, left=0.7, top=1.7, width=11.9, height=5.3, size=18, gap=12):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = it
        p.font.size = Pt(size)
        p.font.color.rgb = INK
        p.space_after = Pt(gap)
        p.line_spacing = 1.3
    return box


def card_text(slide, left, top, width, height, big, label, desc):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = label
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = MUTED
    p1 = tf.add_paragraph()
    p1.text = big
    p1.font.size = Pt(34)
    p1.font.bold = True
    p1.font.color.rgb = PRIMARY
    p1.space_before = Pt(6)
    p2 = tf.add_paragraph()
    p2.text = desc
    p2.font.size = Pt(14)
    p2.font.color.rgb = INK
    p2.space_before = Pt(8)
    p2.line_spacing = 1.25
    return box


# ---------- 1 封面 ----------
s = prs.slides.add_slide(BLANK)
box = s.shapes.add_textbox(Inches(1), Inches(2.1), Inches(11.3), Inches(3.4))
tf = box.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]; p.text = "AI 应用开发工程师"
p.font.size = Pt(54); p.font.bold = True; p.font.color.rgb = INK; p.alignment = PP_ALIGN.CENTER
p2 = tf.add_paragraph(); p2.text = "大模型应用 / Agent 方向"
p2.font.size = Pt(26); p2.font.color.rgb = PRIMARY; p2.alignment = PP_ALIGN.CENTER; p2.space_before = Pt(10)
p3 = tf.add_paragraph(); p3.text = "就业赛道 · 求职综合展示"
p3.font.size = Pt(16); p3.font.color.rgb = ACCENT; p3.alignment = PP_ALIGN.CENTER; p3.space_before = Pt(34)
p4 = tf.add_paragraph(); p4.text = "庄铭湛 · 电子科技大学中山学院 · 人工智能 · 2028 届"
p4.font.size = Pt(16); p4.font.color.rgb = MUTED; p4.alignment = PP_ALIGN.CENTER; p4.space_before = Pt(14)

# ---------- 2 职业目标 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "让大模型能力落地成产品")
box = s.shapes.add_textbox(Inches(0.7), Inches(1.5), Inches(11.9), Inches(1.6))
tf = box.text_frame; tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "我是一名专注 AI 应用开发的 2028 届本科生，目标是把大模型能力真正落地成产品——我用「职镜」证明了这条路。"
p.font.size = Pt(20); p.font.color.rgb = ACCENT; p.line_spacing = 1.4
add_body(s, [
    "岗位：AI 应用研发工程师（大模型应用 / Agent 方向）",
    "行业：人工智能应用层（AIGC / 智能体）",
    "城市：广州 / 深圳",
    "对标企业：阿里巴巴、字节跳动、CVTE、金山办公、唯品会",
], top=3.4)

# ---------- 3 为什么是应用岗 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "应用岗，本科生的蓝海")
card_text(s, 0.7, 1.8, 3.7, 3.6, "12 倍", "风口", "2026 春招 AI 岗位量同比增，占比 2.29% → 26.23%（脉脉）")
card_text(s, 4.8, 1.8, 3.7, 3.6, "60.97%", "方向", "AI 应用开发岗占 AI 岗位六成，最热招是 Agent 开发（脉脉）")
card_text(s, 8.9, 1.8, 3.7, 3.6, "200万→500万", "蓝海", "中国 AI Agent 活跃智能体数量，2026 预计 +145%（IDC）")
box = s.shapes.add_textbox(Inches(0.7), Inches(5.8), Inches(11.9), Inches(1.0))
box.text_frame.text = "📌 7 份真实 JD 拆解结论：应用岗本科可投、算法岗普遍要硕士 → 主攻应用岗"
box.text_frame.paragraphs[0].font.size = Pt(14); box.text_frame.paragraphs[0].font.color.rgb = MUTED

# ---------- 4 我的匹配度 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "应用岗匹配 89 / 86，缺口清零")
card_text(s, 0.7, 1.9, 3.5, 3.0, "89", "阿里 · AI 应用研发", "应用岗")
card_text(s, 4.9, 1.9, 3.5, 3.0, "86", "CVTE · 应用开发", "应用岗")
card_text(s, 9.1, 1.9, 3.5, 3.0, "83", "金山 · 产品经理", "产品岗")
add_body(s, [
    "应用岗 89/86 ＞ 产品 83 ＞ 后端 65 ＞ 算法 55~60",
    "能力标签：动手落地 · AI 应用 · 自驱学习",
], top=5.2, size=17)

# ---------- 5 痛点 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "职镜：解决求职「盲投」")
add_body(s, [
    "痛点：简历不会改 · 投不对岗 · 看不出差距 → 像「盲投」",
    "方案：粘贴 / 上传简历 → 自动出评分、缺口、建议、优化",
    "",
    "目标用户：大三 / 大四求职大学生",
], size=22)

# ---------- 6 技术方案 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "三条技术路径，一个完整作品")
add_body(s, [
    "上传简历（docx/pdf/jpg 等 6 种）→ 规则解析（技能/教育/项目）→ 匹配评分（4 维度/100 分）→ RAG 建议（LangChain + 检索）→ 导出报告",
    "➕ Function Calling 智能选岗助手（查岗位 / 看要求 / 诊断简历）",
    "✨ 简历优化（JD 拆解 + 按岗重写，缺失标【待补充数据】）",
    "角色：全栈独立完成 · 已部署 Streamlit Cloud 线上",
], size=20)

# ---------- 7 试用结果 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "6 位同学真实试用")
card_text(s, 3.2, 1.9, 3.0, 3.0, "6 人", "真实试用", "")
card_text(s, 7.1, 1.9, 3.0, 3.0, "59 分", "平均匹配分", "")
add_body(s, [
    "用户原话：「匹配度挺高，我也有意向向这个方向发展，待提升的分析也够详细。」—— 余华丰（产品经理 77 分）",
    "已部署 Streamlit Cloud 线上，公开可访问",
], top=5.3, size=17)

# ---------- 8 差距与补足 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "诚实差距 + 补足计划")
add_body(s, [
    "① 缺技术岗实习 —— 唯一实习是仓储（非技术），2027 暑期补 AI 方向实习",
    "② 无竞赛获奖 —— 用「职镜」真实试用数据替代背书",
    "③ 软技能待实战 —— 沟通 / 业务理解，在试用与答辩中验证",
    "",
    "2027.3-4 投递暑期实习 → 2027.7-8 暑期实习 → 2027.8 起秋招主批（提前批 2027.6 起）",
], size=20)

# ---------- 9 求职策略 ----------
s = prs.slides.add_slide(BLANK)
add_title(s, "冲稳保 + 时间表")
add_body(s, [
    "🎯 冲：阿里巴巴（AI 应用研发）、阿里巴巴（大模型算法）、字节跳动（推荐算法）",
    "🛡️ 稳：CVTE（应用开发）、金山办公（产品经理 AI 专项）、唯品会（LLM 算法）",
    "🧭 保：本地教育科技（AI 应用 / 大模型实习，BOSS/牛客筛选）",
    "",
    "时间表：2027.3 投暑期实习 → 2027.7 实习 → 2027.8 秋招主批（提前批 2027.6 起）",
], size=19)

# ---------- 10 结尾 ----------
s = prs.slides.add_slide(BLANK)
box = s.shapes.add_textbox(Inches(1), Inches(2.6), Inches(11.3), Inches(2.4))
tf = box.text_frame; tf.word_wrap = True
p = tf.paragraphs[0]; p.text = "让大模型能力，落地成产品。"
p.font.size = Pt(44); p.font.bold = True; p.font.color.rgb = INK; p.alignment = PP_ALIGN.CENTER
p2 = tf.add_paragraph(); p2.text = "这是「职镜」写下的第一行证明，接下来我想在大厂把它继续写大。"
p2.font.size = Pt(20); p2.font.color.rgb = PRIMARY; p2.alignment = PP_ALIGN.CENTER; p2.space_before = Pt(18)

out = "求职综合展示-新版.pptx"
prs.save(out)
print("已生成:", out, "| 页数:", len(prs.slides._sldIdLst))
