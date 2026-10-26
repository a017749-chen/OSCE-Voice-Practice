"""Validate an OSCE practice case and export self-contained voice/text files.

Requires PyYAML and jsonschema. No model, network or overwrite operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import yaml

SKILL = Path(__file__).resolve().parents[1]
SKILLS = SKILL.parent


def native_station(case):
    station = {k: case[k] for k in ("station_type", "number", "sign", "candidate", "examiner", "sp")}
    return {**station, "rubric": "checklist", "checklist": case["rubric"]["items"]}


def validate_case(case, rules):
    schema = json.loads((SKILL / "references/case.schema.json").read_text(encoding="utf-8"))
    errors = [f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
              for e in jsonschema.Draft202012Validator(schema).iter_errors(case)]
    if errors:
        raise ValueError("Schema validation failed:\n" + "\n".join(errors))
    items, facts = case["rubric"]["items"], case["facts"]
    n, conf = len(items), rules["checklist"]
    fact_ids = [f["id"] for f in facts]
    item_ids = [i["id"] for i in items]
    if len(fact_ids) != len(set(fact_ids)) or len(item_ids) != len(set(item_ids)):
        errors.append("Duplicate fact/item ID")
    if len({q["id"] for q in case["active_questions"]}) != len(case["active_questions"]):
        errors.append("Duplicate active-question ID")
    for item in items:
        if set(item["fact_ids"]) - set(fact_ids):
            errors.append(f"{item['id']}: unknown fact IDs")
        if len(set(item["anchors"].values())) != len(item["anchors"]):
            errors.append(f"{item['id']}: identical scoring anchors")
    if not conf["items_min"] <= n <= conf["items_max"]:
        errors.append("Checklist item count outside canonical rules")
    if case["rubric"]["max_score"] != 2 * n:
        errors.append("max_score must equal 2*N")
    stars = sum(i["star"] for i in items)
    if not conf["high_discrimination_min"] <= stars <= conf["high_discrimination_max"]:
        errors.append("Star-item count outside canonical rules")
    if sum(i["generic"] for i in items) > conf["generic_items_max"]:
        errors.append("Too many generic items")
    if sum(i["main_construct"] for i in items) < math.ceil(n * conf["main_construct_min_fraction"]):
        errors.append("Too few main-construct items")
    if case["station_type"] == "history":
        limit = math.floor(n * rules["station_types"]["history"]["lqqopera_max_fraction"])
        if sum(i["lqqopera"] for i in items) > limit:
            errors.append("Too many LQQOPERA groups")
    questions = case["active_questions"]
    if len(questions) > rules["sp"]["questions_max"]:
        errors.append("Too many active SP questions")
    if sum(bool(q["item_ids"]) for q in questions) > rules["sp"]["scoring_questions_max"]:
        errors.append("Too many scoring-related active SP questions")
    for question in questions:
        for item_id in question["item_ids"]:
            if item_id not in item_ids:
                errors.append(f"{question['id']}: unknown item {item_id}")
            elif not next(i for i in items if i["id"] == item_id)["sp_prompted"]:
                errors.append(f"{item_id}: missing sp_prompted marker")
    for key, text in (("sign_patient_info_chars", case["sign"]),
                      ("candidate_background_chars", case["candidate"]["background"])):
        if len(text) > rules["limits"][key]:
            errors.append(f"{key} exceeded")
    if len(case["candidate"]["tasks"]) > rules["limits"]["candidate_tasks_max"]:
        errors.append("Too many candidate tasks")
    if len(case["examiner"]["differentials"]) < rules["limits"]["differentials_min"]:
        errors.append("Too few differentials/care contexts")
    if sum(row.get("question", False) for row in case["sp"]["dialogue"]) > rules["sp"]["dialogue_question_rows_max"]:
        errors.append("Too many SP dialogue question rows")
    if rules["station_types"][case["station_type"]].get("teach_back_required"):
        if not any("teach" in d["frame"].lower() or "回述" in d["frame"] for d in case["sp"]["dialogue"]):
            errors.append("Missing teach-back dialogue")
    if errors:
        raise ValueError("Case validation failed:\n" + "\n".join(errors))


def runtime_text(rules):
    sp = (SKILLS / "osce-standardized-patient/assets/runtime-instructions.txt").read_text(encoding="utf-8")
    fb = (SKILLS / "osce-practice-feedback/assets/feedback-instructions.txt").read_text(encoding="utf-8")
    return (sp + "\n\n" + fb + "\n\n【本站使用的規則數值】\n" +
            f"時間 {rules['station']['minutes']} 分鐘（由外部計時）；劇本 SP 提問後相應項目最高 "
            f"{rules['sp']['prompted_item_score_cap']} 分。\n")


def candidate_text(case, rules):
    cand = case["candidate"]
    report = "\n".join(f"- {key}：{value}" for key, value in cand["report"].items())
    return (f"# {case['station_id']} 考生指引\n\n"
            f"版本：{case['case_version']}｜虛構教學情境｜對象：{case['learner']}\n\n"
            f"背景：{cand['background']}\n\n任務：\n" +
            "\n".join(f"- {task}" for task in cand["tasks"]) +
            f"\n\n時間：{rules['station']['minutes']} 分鐘，請使用外部計時器。\n\n" +
            "\n".join(f"- {note}" for note in cand["notes"]) +
            f"\n\n可取得資料：{cand['available_data']}\n\n{report}\n")


def lesson_text(case, rules):
    n = len(case["rubric"]["items"])
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    lines = [f"# {case['title']} 完整教案", "", f"版本：{case['case_version']}｜日期：{today}｜虛構教學病例",
             "狀態：AI 編製形成性練習示範；教師審閱與真人語音實測狀態見 case.json 及 QA 紀錄。",
             "", "## 藍圖與能力對齊", case["design"]["objective"], case["design"]["core_task"],
             f"{rules['station']['minutes']} 分鐘；{n} 項 0/1/2 分，滿分 {case['rubric']['max_score']} 分。",
             *case["design"]["competencies"], *case["design"]["decisions"],
             "", "## 一 告示牌", f"第 {case['number']} 站", case["sign"],
             "", "## 二 考生指引", candidate_text(case, rules), "", "## 三 評分表",
             "★為設計上希望區辨的項目，尚未取得實證鑑別度。", "",
             "| ID | 可觀察行為 | 0 分 | 1 分 | 2 分 | SP 事實對應 |", "|---|---|---|---|---|---|"]
    for i in case["rubric"]["items"]:
        lines.append(f"| {i['id']} | {'★' if i['star'] else ''}{i['text']} | {i['anchors']['0']} | {i['anchors']['1']} | {i['anchors']['2']} | {', '.join(i['fact_ids'])} |")
    lines += ["", "整體表現 1–5（與條列分數分開）："]
    lines += [f"- {k}：{v}" for k,v in case["rubric"]["global_anchors"].items()]
    lines += ["", "## 四 考官指引", "本包為形成性練習；Word 模板內的官方考官提示文字應配合教學用途解讀。",
              case["examiner"]["summary"], "鑑別／照護脈絡：" + "、".join(case["examiner"]["differentials"]),
              "場景：" + case["examiner"]["setting"], "人員／道具：" + case["examiner"]["props"],
              "評分依上述逐項錨點，不另加未定義扣分或通過線。純語音不評身體檢查及非語言行為。",
              "SP 劇本摘要：" + case["sp"]["summary"], "", "## 五 SP 指引", case["patient"]["identity"],
              "起始姿勢：" + case["sp"]["start_position"], "情緒：" + case["sp"]["emotion"],
              "表情與肢體（供真人 SP）：" + case["sp"]["manner"], "語氣：" + case["sp"]["voice"],
              "開場：" + case["patient"]["opening"], case["sp"]["principles"],
              case["patient"]["emotion_rules"], "Teach-back：" + case["patient"]["teach_back"],
              "未知資訊：" + case["patient"]["unknown_response"], "", "| 事實 ID | 觸發條件 | 固定回應內容 |", "|---|---|---|"]
    lines += [f"| {f['id']} | {f['trigger']} | {f['response']} |" for f in case["facts"]]
    lines += ["", "| 病歷架構 | 考生可能說的話 | SP 的回應或提問 |", "|---|---|---|"]
    lines += [f"| {d['frame']} | {d['candidate']} | {d['sp']} |" for d in case["sp"]["dialogue"]]
    lines += ["", "主動提問："]
    lines += ([f"- {q['trigger']}：{q['text']}；影響項目 {','.join(q['item_ids']) or '無'}。實際提示後上限 {rules['sp']['prompted_item_score_cap']} 分。" for q in case["active_questions"]]
              or ["- 無主動提問；只回應考生。"])
    lines += ["", "診間示意圖：" + case["sp"]["room_diagram"], "", "## SP 訓練與場地檢核",
              "- 核對站次與版本，逐項排演事實揭露、重複詢問與情緒轉移。",
              "- 準備考生資料、安靜場地、語音設備及外部倒數；核對可取得報告。",
              "- 演練開始不透露答案；只使用預定主動提問；結束後才回饋。",
              "- 教師確認臨床內容、8 分鐘可行性、規準品質及聲音辨識情形後再用於課程。",
              "", "## 來源與限制", "病例身分、病程與數值均為虛構設計；外部來源支持知識背景，未驗證本題效度。"]
    lines += [f"- [{s['id']}]({s['url']})：{s['use']}；覆核 {s['checked']}。" for s in case["sources"]]
    lines += ["", "原始驗證註記（實際完成結果另見 QA 紀錄）：", json.dumps(case["validation"], ensure_ascii=False, indent=2)]
    return "\n".join(lines) + "\n"


def export_case(case_path, rules_path, output):
    case = json.loads(Path(case_path).read_text(encoding="utf-8"))
    rules = yaml.safe_load(Path(rules_path).read_text(encoding="utf-8"))
    validate_case(case, rules)
    prompt = runtime_text(rules)
    candidate = candidate_text(case, rules)
    packet = ("OSCE 語音演練包\n" + f"站次 {case['station_id']}／版本 {case['case_version']}\n"
              "本檔包含延後揭露的教學答案，持有人可閱讀。只用於虛構病例練習。\n\n" + prompt +
              "\n【考生可見指引】\n" + candidate + "\n【病例資料 JSON 僅依規則使用，結束前不要完整朗讀】\n" +
              json.dumps(case, ensure_ascii=False, indent=2) + "\n")
    payload = {"考生指引.md": candidate, "完整教案.md": lesson_text(case, rules),
               "語音演練包.txt": packet, "教案內容.yaml": yaml.safe_dump(native_station(case), allow_unicode=True, sort_keys=False)}
    output = Path(output)
    if any((output / name).exists() for name in [*payload, "package-manifest.json"]):
        raise FileExistsError("Refusing to overwrite an existing export; use a new output directory.")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"station_id": case["station_id"], "case_version": case["case_version"],
                "source_sha256": hashlib.sha256(Path(case_path).read_bytes()).hexdigest(),
                "rules_sha256": hashlib.sha256(Path(rules_path).read_bytes()).hexdigest(),
                "runtime_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "files": {}}
    for name, content in payload.items():
        target = output / name
        target.write_text(content, encoding="utf-8")
        manifest["files"][name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "package-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case")
    p.add_argument("--rules", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    export_case(args.case, args.rules, args.out)
    print("Validated and exported OSCE practice package.")


if __name__ == "__main__":
    main()
