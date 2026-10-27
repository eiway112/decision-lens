#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""决策透镜简报机检。

判定对象
    本技能自身产出的「八要素推理架构简报」（Markdown 文件或 stdin）。

判据（每条都能机检；发现 0 个检查对象即 FAIL，不许静默通过）
    B1  输入非空且 >= 200 字符，否则零命中 FAIL
    B2  八要素小节 ①-⑧ 全部命中且正文非空；一个都不命中 -> 零命中 FAIL
    B3  已选透镜数 ∈ [1,3]（0 说明不该走本流程；>=4 判无差别套用）
    B4  每个被选透镜含「什么证据会推翻」且非占位
    B5  每个被选透镜的「改变了哪个决策」含转折标记
    B6  每个被选透镜含「何时不该用」且非占位
    B7  「未选用透镜及理由」>= 2 条且理由非空（反向闸门）
    B8  已选透镜按 8 个互斥组去重后数量不变（同组最多 1）
    B9  要素⑥条目 >= 1 且每条标注来源（pre-mortem / 反例 / 边界）
    B10 要素⑧落到具名能力，不含「继续分析」类空话
    B11 全文无 [TODO] / 待补 / XXX / （略）
    B12 全文无盘符 / 家目录 / UNC 路径

用法
    python check_lens_brief.py <简报.md>
    python check_lens_brief.py --stdin < 简报.md
    python check_lens_brief.py --check-catalog        # 校验 30 格映射表
    python check_lens_brief.py --selftest             # 缺陷注入自检（改判据后必跑）
    python check_lens_brief.py --help

退出码（对齐容器主线：sync_skills.py / check_claims.py）
    0  扫描完成，无 FAIL
    1  有 FAIL（含零命中）
    2  用法或配置错误（没给输入、路径不存在、编码失败、参数非法）

零命中归 1 不归 2：文件存在但读不到简报内容 = 检查跑了并判出 FAIL；
只有「根本没跑起来」才配 2。
"""

import argparse
import io
import os
import re
import sys

ELEMENTS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"]
ELEMENT_NAMES = {
    "①": "原始问题与被掩盖的问题", "②": "当前隐含假设", "③": "选中的透镜及理由",
    "④": "每个透镜改变了哪个决策", "⑤": "非显然推论", "⑥": "反例与失败条件",
    "⑦": "适用边界", "⑧": "下一步交给谁",
}
LENS_RE = re.compile(r"(?<![A-Za-z0-9])([DPM]-\d{2})(?![A-Za-z0-9])")
MIN_CHARS = 200

# 占位词：只用于判定字段值，不用于全文扫描（避免正常破折号被误判）
PLACEHOLDERS = ("暂无", "待定", "N/A", "n/a", "NA", "（略）", "(略)", "无", "-", "—")
# 全文级占位符（B11）
GLOBAL_PLACEHOLDERS = ("[TODO]", "TODO", "待补", "XXX", "（略）")
# 交接空话（B10）
EMPTY_TALK = ("继续分析", "后续再定", "待定", "再说", "进一步研究", "看看再说", "再想想")

# 同族互斥组（与 references/forms-and-routing.md §八 保持一致）
MUTEX_GROUPS = {
    "角色分离": {"M-02", "M-05", "D-08"},
    "对照与净贡献": {"M-03", "M-04"},
    "数字口径": {"M-06", "M-07", "P-10"},
    "分层不对称": {"D-02", "D-05", "D-07"},
    "边界与停止": {"M-09", "P-01", "D-15", "D-16"},
    "归因定位": {"P-03", "P-11", "P-07", "P-06"},
    "衰减与失效": {"D-17", "P-09", "M-10"},
    "存在性判据": {"D-01", "D-13", "D-12"},
}

SOURCE_TAGS = ("pre-mortem", "反例", "边界")

# 家目录形态用拼接构造：本文件若出现该形态的字面量，仓内脱敏扫描会命中判据定义本身，
# 从而让「零命中」判据永远失败。拼接不影响判据语义。
HOME_PAT = r"(?<![A-Za-z0-9])" + "~" + r"/"
HOME_LIT = "~" + "/"


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


def split_elements(text):
    """按 '## ①' … '## ⑧' 切分，返回 {mark: body}。"""
    marks = [(m.start(), m.group(1))
             for m in re.finditer(r"(?m)^##\s*([①②③④⑤⑥⑦⑧])\s*.*$", text)]
    out = {}
    for i, (pos, mark) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        nl = text.find("\n", pos)
        out.setdefault(mark, "")
        out[mark] += text[nl + 1:end]
    return out


def field_value(block, label):
    """取 '- **label**：值' 的值；找不到返回 None。"""
    m = re.search(r"\*\*" + label + r"\*\*\s*[:：]?\s*(.*)$", block, re.M)
    if not m:
        return None
    return m.group(1).strip()


def is_placeholder(v):
    return (not v) or (v.strip() in PLACEHOLDERS)


def check_text(text):
    """返回 [(编号, 失败文案)]，空列表即通过。"""
    f = []
    text = (text or "").replace("\r\n", "\n")

    # ---- B1 输入非空 ----
    if len(text.strip()) < MIN_CHARS:
        f.append(("B1", "零命中：正文 %d 字符，不足 %d，检查输入路径或管道"
                  % (len(text.strip()), MIN_CHARS)))

    secs = split_elements(text)

    # ---- B2 八要素 ----
    if not secs:
        f.append(("B2", "零命中：未找到任何八要素小节，判定对象不是推理架构简报"))
    else:
        for mark in ELEMENTS:
            if mark not in secs:
                f.append(("B2", "第 %s 要素缺失：%s" % (mark, ELEMENT_NAMES[mark])))
            elif not secs[mark].strip():
                f.append(("B2", "第 %s 要素为空：%s" % (mark, ELEMENT_NAMES[mark])))

    # ---- B3 已选透镜数 ----
    selected = []
    if "③" in secs:
        for m in LENS_RE.finditer(secs["③"]):
            if m.group(1) not in selected:
                selected.append(m.group(1))
    if len(selected) == 0:
        f.append(("B3", "未选中任何透镜：本技能只在选出 1-3 个时成立，"
                        "选 0 个说明这个问题不该走本流程"))
    elif len(selected) > 3:
        f.append(("B3", "选中 %d 个透镜（上限 3）：判定为无差别全量套用，"
                        "撤下决策增量最弱的 %d 个" % (len(selected), len(selected) - 3)))

    # ---- B4 / B5 / B6 逐透镜字段 ----
    blocks = {}
    if "④" in secs:
        for raw in re.split(r"(?m)^###\s+", secs["④"])[1:]:
            ids = LENS_RE.findall(raw.split("\n")[0])
            if ids:
                blocks[ids[0]] = raw
    for lens in selected:
        blk = blocks.get(lens)
        if blk is None:
            f.append(("B4", "透镜 %s 在要素④中无对应小节：选了就要逐个交代" % lens))
            continue
        v = field_value(blk, "什么证据会推翻")
        if v is None:
            f.append(("B4", "透镜 %s 缺「什么证据会推翻」字段："
                            "没有可被推翻条件的透镜不参与决策" % lens))
        elif is_placeholder(v):
            f.append(("B4", "透镜 %s 的证伪条件是占位值（%s）："
                            "占位等于没写" % (lens, v)))
        v = field_value(blk, "改变了哪个决策")
        if v is None:
            f.append(("B5", "透镜 %s 缺「改变了哪个决策」字段："
                            "填不出即为装饰性透镜，撤下" % lens))
        elif not (re.search(r"原(来|先)?(打算|计划|准备|认为)", v)
                  and re.search(r"改为|改成|改换|换为|不再|撤下", v)) \
                and "→" not in v:
            f.append(("B5", "透镜 %s 未绑定决策增量：需写成"
                            "「原打算 X → 改为 Y」，含转折标记" % lens))
        v = field_value(blk, "何时不该用")
        if v is None:
            f.append(("B6", "透镜 %s 缺「何时不该用」字段（边界密度要求 100%%）" % lens))
        elif is_placeholder(v):
            f.append(("B6", "透镜 %s 的「何时不该用」是占位值（%s）" % (lens, v)))

    # ---- B7 反向闸门 ----
    m = re.search(r"(?m)^##\s*未选用透镜[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S)
    if not m:
        f.append(("B7", "缺少「未选用透镜及理由」小节：需 >= 2 个强透镜 + 具体弃用理由"))
    else:
        items = [x for x in re.findall(r"(?m)^-\s+(.+)$", m.group(1)) if x.strip()]
        if len(items) < 2:
            f.append(("B7", "弃用记录只有 %d 条（需 >= 2）："
                            "反向闸门要求给出具体弃用理由" % len(items)))
        for it in items:
            if "因为" not in it and "由于" not in it and "：" not in it and ":" not in it:
                f.append(("B7", "弃用理由未说明原因：%s" % it[:40]))

    # ---- B8 同族互斥 ----
    for gname, members in MUTEX_GROUPS.items():
        hit = [x for x in selected if x in members]
        if len(hit) > 1:
            f.append(("B8", "同族透镜重复选用：%s 组出现 %s，同组最多 1 个"
                      % (gname, "/".join(hit))))

    # ---- B9 反例与失败条件 ----
    if "⑥" in secs:
        items = [x for x in re.findall(r"(?m)^-\s+(.+)$", secs["⑥"]) if x.strip()]
        if not items:
            f.append(("B9", "第⑥要素条目数 0：反例与失败条件不可省"))
        for it in items:
            src = re.search(r"来源\s*[:：]\s*(.*)$", it)
            if not src or src.group(1).strip() not in SOURCE_TAGS:
                f.append(("B9", "第⑥要素条目未标注来源（须为 pre-mortem / 反例 / 边界"
                                " 之一）：%s" % it[:40]))

    # ---- B10 交接 ----
    if "⑧" in secs:
        cands = re.findall(r"能力\s*[:：]\s*([^\n]+)", secs["⑧"])
        cands = [c.strip() for c in cands if c.strip()]
        if not cands:
            f.append(("B10", "第⑧要素未落到具体能力："
                             "必须指名交给哪个执行或验证能力"))
        for c in cands:
            if any(k in c for k in EMPTY_TALK):
                f.append(("B10", "第⑧要素是空话（%s）：必须落到具名能力" % c[:40]))

    # ---- B11 占位符 ----
    for tok in GLOBAL_PLACEHOLDERS:
        if tok in text:
            f.append(("B11", "占位符残留：%s" % tok))

    # ---- B12 本机路径 ----
    for pat in (r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]", HOME_PAT, r"\\\\[A-Za-z0-9]"):
        m2 = re.search(pat, text)
        if m2:
            f.append(("B12", "简报含本机路径：%s" % m2.group(0)))
            break

    return f


# ---------------------------------------------------------------- 目录自检
def check_catalog(skill_dir):
    """校验 30 格映射表：空格数 == 0，未被映射的透镜 id 数 == 0。"""
    f = []
    ref = os.path.join(skill_dir, "references")
    routing = os.path.join(ref, "forms-and-routing.md")
    if not os.path.exists(routing):
        return [("C0", "缺 %s，无法校验目录" % routing)]

    all_ids = set()
    for name in sorted(os.listdir(ref)):
        if name.startswith("lens-") and name.endswith(".md"):
            all_ids |= set(LENS_RE.findall(read(os.path.join(ref, name))))

    text = read(routing)
    mapped, empties, rows = set(), 0, 0
    for chunk in re.split(r"(?m)^###\s+A\s*=\s*", text)[1:]:
        for b, lenses in re.findall(r"(?m)^\|\s*([^|\n]+?)\s*\|\s*([^|\n]*)\s*\|\s*$", chunk):
            bb = b.strip()
            if bb in ("B", "透镜") or set(bb) <= set("-: "):
                continue
            rows += 1
            if not lenses.strip():
                empties += 1
            mapped |= set(LENS_RE.findall(lenses))

    if rows != 30:
        f.append(("C1", "映射表识别到 %d 行，期望 30 行（5 因果域 × 6 决策类型），先查解析" % rows))
    if empties:
        f.append(("C2", "空格数 %d（须为 0）：每一格都要预登记 1-3 个透镜" % empties))
    zombies = sorted(all_ids - mapped)
    if zombies:
        f.append(("C3", "僵尸透镜 %d 个（未被任何格映射）：%s"
                  % (len(zombies), ", ".join(zombies))))
    ghosts = sorted(mapped - all_ids)
    if ghosts:
        f.append(("C4", "映射表引用了不存在的透镜 %d 个：%s"
                  % (len(ghosts), ", ".join(ghosts))))
    return f


# ---------------------------------------------------------------- 缺陷注入自检
def _drop_section(t, mark_start, mark_end):
    return re.sub(r"(?ms)^##\s*" + mark_start + r".*?(?=^##\s*" + mark_end + r")", "", t)


def _drop_first_line(t, needle):
    lines = t.split("\n")
    for i, ln in enumerate(lines):
        if needle in ln:
            del lines[i]
            return "\n".join(lines)
    return t


def _replace_field(t, label, new_value):
    return re.sub(r"(\*\*" + label + r"\*\*\s*[:：]?\s*)(.*)$",
                  lambda m: m.group(1) + new_value, t, count=1, flags=re.M)


MUTATORS = [
    ("M01 清空全文→B1", lambda t: "", "B1"),
    ("M02 删第⑦要素→B2", lambda t: _drop_section(t, "⑦", "⑧"), "B2"),
    ("M03 透镜加到4个→B3", lambda t: t.replace(
        "\n## ④", "\n- M-12 · 机制上线前过双门槛——选择理由：测试注入\n"
                 "- P-05 · 小世界 / 大世界——选择理由：测试注入\n\n## ④"), "B3"),
    ("M04 删证伪条件→B4", lambda t: _drop_first_line(t, "什么证据会推翻"), "B4"),
    ("M05 决策增量改复述→B5",
     lambda t: _replace_field(t, "改变了哪个决策", "核对工作会更自动化，效率会提高"), "B5"),
    ("M06 删何时不该用→B6", lambda t: _drop_first_line(t, "何时不该用"), "B6"),
    ("M07 删弃用记录→B7",
     lambda t: re.sub(r"(?ms)^##\s*未选用透镜.*$", "", t), "B7"),
    ("M08 换成同族透镜→B8", lambda t: t.replace("D-06", "D-01"), "B8"),
    ("M09 删反例条目→B9",
     lambda t: re.sub(r"(?ms)(^##\s*⑥.*?)(?=^##\s*⑦)",
                      lambda m: "## ⑥ 反例与失败条件\n\n", t), "B9"),
    ("M10 交接改空话→B10",
     lambda t: re.sub(r"(?m)^-\s*能力\s*[:：].*$", "- 能力：继续分析", t), "B10"),
    ("M11 插入 TODO→B11", lambda t: t + "\n[TODO] 待补\n", "B11"),
    ("M12 插入本机路径→B12", lambda t: t + "\n备份在 " + HOME_LIT + "some/path\n", "B12"),
]


def selftest(skill_dir):
    sample = os.path.join(skill_dir, "references", "worked-example.md")
    if not os.path.exists(sample):
        print("缺合法样本：%s" % sample, file=sys.stderr)
        return 1
    base = read(sample)
    ok = True

    # 正向：合法样本必须零误报
    f0 = check_text(base)
    if f0:
        ok = False
        print("[FAIL] 合法样本误报 %d 项：" % len(f0), file=sys.stderr)
        for code, msg in f0:
            print("       %s %s" % (code, msg), file=sys.stderr)
    else:
        print("[OK]   合法样本零误报（%d 字符）" % len(base))

    # 负向：12 个 mutator 必须全部被捕获
    for name, fn, expect in MUTATORS:
        mutated = fn(base)
        if mutated == base:
            ok = False
            print("[FAIL] %s：mutator 没改动文本，注入失败" % name, file=sys.stderr)
            continue
        f = check_text(mutated)
        codes = [c for c, _ in f]
        if expect not in codes:
            ok = False
            print("[FAIL] %s：期望捕获 %s，实际 %s" % (name, expect, codes or "无"),
                  file=sys.stderr)
        else:
            print("[OK]   %s → 捕获 %s" % (name, expect))

    # 目录自检一并跑
    cf = check_catalog(skill_dir)
    if cf:
        ok = False
        for code, msg in cf:
            print("[FAIL] 目录自检 %s %s" % (code, msg), file=sys.stderr)
    else:
        print("[OK]   目录自检：30 格无空格、无僵尸透镜")

    print("\nSELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="决策透镜简报机检（B1-B12）+ 目录自检 + 缺陷注入自检",
        epilog="退出码：0 无 FAIL ｜ 1 有 FAIL（含零命中）｜ 2 用法或配置错误")
    ap.add_argument("brief", nargs="?", help="简报 Markdown 路径")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 读简报")
    ap.add_argument("--check-catalog", action="store_true", help="校验 30 格映射表")
    ap.add_argument("--selftest", action="store_true", help="缺陷注入自检")
    ap.add_argument("--verbose", action="store_true", help="打印全部判据读数")
    args = ap.parse_args(argv)

    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.selftest:
        return selftest(skill_dir)

    if args.check_catalog:
        f = check_catalog(skill_dir)
        for code, msg in f:
            print("FAIL %s %s" % (code, msg), file=sys.stderr)
        if not f:
            print("CATALOG OK：30 格无空格、无僵尸透镜")
        return 1 if f else 0

    if args.stdin:
        try:
            text = sys.stdin.read()
        except Exception as exc:
            print("读取 stdin 失败：%s" % exc, file=sys.stderr)
            return 2
    elif args.brief:
        if not os.path.exists(args.brief):
            print("路径不存在：%s" % args.brief, file=sys.stderr)
            return 2
        try:
            text = read(args.brief)
        except Exception as exc:
            print("读取失败（编码？）：%s" % exc, file=sys.stderr)
            return 2
    else:
        print("未给输入：需要 <简报.md> 或 --stdin；用法见 --help", file=sys.stderr)
        return 2

    f = check_text(text)
    for code, msg in sorted(f):
        print("FAIL %s %s" % (code, msg), file=sys.stderr)
    if not f:
        sel = LENS_RE.findall(split_elements(text).get("③", ""))
        print("BRIEF OK：八要素齐全，选中透镜 %d 个（%s）"
              % (len(set(sel)), ", ".join(sorted(set(sel))) or "无"))
    if args.verbose:
        print("字符数 %d ｜ 判据 B1-B12" % len(text))
    return 1 if f else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
