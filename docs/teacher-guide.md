# 教師與維護說明

本專案提供病史詢問與醫病溝通兩種虛構示範，以及從 idea 生成教案、扮演病人、結束後回饋的指令。每題有考生指引、完整教案、語音包及 `case.json`；語音包可直接交給網頁版 ChatGPT。

## 教師使用前

1. 對照學員程度與教學目標，審閱臨床情境、陽性與陰性線索、病人可能的回答和情緒變化。
2. 依各項 0／1／2 錨點練習評分；確認觸及評分項目的 SP 提問條件與分數上限。
3. 讓學生以外部 8 分鐘計時試跑，核對語音辨識、病例一致性及回饋與逐字稿是否相符。
4. 缺乏完整逐字稿時，將無法判斷的項目列 NA，僅報可評項目小計。不得將缺段直接視為未做到。

兩題現階段尚未完成人類語音測試、教師臨床審閱或評分校準；不宣稱正式考試效度。

## 病例來源與同步

每題的 `examples/<站次>/case.json` 是此公開版的病例資料來源；`candidate.md`、`lesson.md`、`voice-packet.txt` 與 `lesson.yaml` 是匯出結果。修改病例時，應重新匯出並檢查不同檔案的一致性；不要手動只改其中一份後當作同步完成。Word 需另行產生或編修並逐頁檢視。

兩份附帶 Word 使用既有教案格式作底稿；公開副本清理了原範本文件屬性，並把考官任務提示改為形成性練習用語。原格式與參考教案不等同最新國考規範。

臨床內容背景：

- HX-001：[NIDDK 膽結石症狀與原因](https://www.niddk.nih.gov/health-information/digestive-diseases/gallstones/symptoms-causes)，查閱於 2026-10-26。示範病人並未確診。
- COM-001：[NIDDK 糖尿病前期](https://www.niddk.nih.gov/health-information/diabetes/overview/what-is-diabetes/prediabetes-insulin-resistance)，查閱於 2026-10-26。個案三個月回診為虛構情境設定，並非通用追蹤間隔。

## 可重現匯出

以下步驟供願意使用命令列的教師或開發者；學生使用現有 TXT 演練包不需要執行。

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python .agents/skills/osce-practice-coordinator/scripts/package_case.py examples/HX-001/case.json --rules rules.practice.yaml --out output/HX-001
python .agents/skills/osce-practice-coordinator/scripts/package_case.py examples/COM-001/case.json --rules rules.practice.yaml --out output/COM-001
python -m unittest discover -s tests -v
```

匯出工具不連網、不呼叫模型、不自動開始語音，並拒絕覆寫既有輸出。它輸出考生指引、完整 Markdown 教案、語音演練包、YAML 與雜湊清單；**不輸出 Word**。此處使用的 `rules.practice.yaml` 是此公開發行版的教學預設快照；教師應依所在地、機構與現行測驗規範另行確認。

三個技能必須同放在 `.agents/skills` 下：匯出工具會讀取相鄰 SP 和回饋技能的固定指令，才能建立自含的演練包。

## 發行維護

公開倉庫的技能和規則是供外部學生使用的發布快照。更新時，維護者應先同步檢查教案來源、版本、兩套示範、規則數值與匯出測試，再以 Git 記錄發布版本。不要上傳任何可識別病人的原始資料。
