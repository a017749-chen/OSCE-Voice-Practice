# 病例交換格式 1.0

`case.json` 是單一病例的可編輯來源，沒有真實病人資料。Schema 只檢查結構，不證明臨床正確或病人行為可靠。

| 欄位 | 用途 |
|---|---|
| schema_version / station_id / case_version | 格式版本、穩定題號與病例版本 |
| title / fictional / learner / mode | 教師題名、虛構標記、學員程度與預設練習模式 |
| design | 主要評量目標、核心任務、能力對齊及設計決定 |
| station_type / number / sign / candidate | 對應既有 TAME builder 的站型、站號、告示牌與考生指引 |
| examiner / sp | 既有 builder 的考官及 SP 指引；包括對白表與房間文字示意圖 |
| patient | 身分、開場白、未知資訊回答、情緒轉移與 teach-back 行為 |
| facts | 病人固定事實；每項有唯一 ID、揭露觸發條件及自然語言回答 |
| active_questions | 允許的主動提問及觸發時機；item_ids 標出可能提示的計分項目 |
| rubric | items、max_score、global_anchors；items 是唯一評分來源，產檔時轉為 checklist |
| sources | 來源 ID、URL、用途、覆核日期；病例數值標記為虛構設計 |
| validation | 結構、文字演練、語音實測、教師審閱等獨立狀態 |

## 評分項目

每項包含 id、text、anchors（字串鍵 0、1、2）、fact_ids；star、generic、main_construct、lqqopera、sp_prompted 是標準化檢查用的布林標記。標記不取代對題意的人工判斷。main_construct 與 lqqopera 分組在設計階段確認，不能靠改標記規避比例規則。sp_prompted 表示此項可能被既定主動提問提示，只有實際發生後才套用上限。

每個 SP 相關項目至少連結一個 fact；純考生說明項目可連結病人理解／回應 fact。facts、examiner.summary、sp.summary 若重述相同資訊，必須交叉核對；工具不能自動判斷語意矛盾。

## 可見與延後揭露

candidate 的內容可以先顯示；其餘資料在練習中只讓模型依規則使用，結束後可回饋。這是延後揭露，不是存取控制。避免用 diagnosis 題名命名學生看到的考生檔案；輸出資料夾使用站次代碼。

## 計時、逐字稿與提示

不預設模型有時鐘。學生使用外部倒數，結束以口令為準。逐字稿完整性於練習後根據實際紀錄填寫，原病例不寫入虛假的試跑結果。教學提示與劇本主動提問分開記錄。NA 不當作 0；不將部分項目重新換算完整成績。

## 產生原生教案

packer 從 case 提取 station_type、number、sign、candidate、examiner、sp，並把 rubric.items 寫入 checklist，rubric 固定為 checklist。字級、頁邊、SP 數字限制及滿分驗證讀取執行者傳入的 canonical rules.yaml。不得為了讓工具通過而自動修正題目或刪減評分項目。
