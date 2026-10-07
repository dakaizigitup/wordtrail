# NAER 医学学术名词署名与许可

## 必需署名

資料提供機關：國家教育研究院，2026，《國家教育研究院-醫學學術名詞》（2026-06-24 釋出版本）。本開放資料依政府資料開放授權條款（Open Government Data License）第1版提供，遵守該條款後可利用。授權條款：https://data.gov.tw/license 。

Data Providing Organization: National Academy for Educational Research, 2026, “Medical Academic Terms” (release dated 2026-06-24). This dataset is made available under the Open Government Data License, version 1.0; use is subject to its terms. License: https://data.gov.tw/license .

資料集頁面：https://taic.moda.gov.tw/datasets/4ca6b322-b160-41dd-a16a-02249f540bf8 。

## 本專案使用與修改

本專案保存該資料集的 CSV 快照 `sources/naer/medical-academic-terms-2026-06-24.csv`，用它建立可輸入的中英候選。來源發布頁標示提供機構為國家教育研究院、資料於2026-06-24上架並更新、授權為政府資料開放授權條款第1版，並報告655,058個 tokens。固定 CSV 有30,797筆資料列，檔案大小1,457,660 bytes，SHA-256 為 `5dfdea2f57d5cb9826006265f73d37d73dadc8dbc205bf317c9ddd09ec859537`；頁面與下載資源識別碼及固定快照資訊記在 `sources/naer/dataset.json`。

修改方式：只保留單個英文詞面、具本機英式或美式音標、ECDICT 名詞詞性證據、本機拼音可達、且尚未存在相同中英對應的條目。繁體中文使用 OpenCC `t2s` 轉成簡體。745組候選映射中，591組連到本機已存在的英文詞頭，留待後續審查；154組涉及136個新英文詞頭並逐項審查，接受57組、排除12組、暫緩85組。運行詞庫只包含接受的57組對應和57個醫學標籤成員；不在按鍵時載入或掃描30,797列來源表。

每列的「來源網站」欄在固定 CSV 中是字面值 `[url]`，沒有可用的逐詞網址。因此本專案只聲稱逐詞對應取自國家教育研究院此公開資料集，不聲稱自行查驗了每個詞的原始外部來源。採納項目還經本機詞性、音標、拼音和人工孤立詞義審查；未將來源整表等同於醫學術語完整範圍，也不宣稱90%覆蓋率。

逐項候選、決定與理由見 `batches/24-naer-medical-reviewed.tsv`；篩選總表、來源散列、輸出散列和統計見 `batches/24-naer-medical-prefilter.tsv`、`naer-medical-manifest.json`。可由 `python scripts/build_naer_medical_batch.py` 確定性重建。

批次25仍使用同一個 NAER 來源和上述署名，另以 NLM MeSH 2026 英文主題關聯及 ECDICT MIT 精確名詞義作交叉核對，不使用 MeSH 中文翻譯。從591組已有英文詞頭候選中篩出45組雙重命中，接受37組、排除3組、暫緩5組，新增18個醫學標籤成員，沒有新增英文詞頭。逐項證據、輸出散列與構建方式見 `batches/25-naer-medical-existing-headwords-reviewed.tsv`、`batches/25-naer-medical-existing-headwords-prefilter.tsv`、`naer-medical-manifest-2.json` 和 `python scripts/build_naer_medical_batch_2.py`。MeSH 署名與下載條件：https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html 。
