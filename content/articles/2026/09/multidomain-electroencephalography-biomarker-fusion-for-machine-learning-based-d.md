---
{
  "title": "多領域脳波バイオマーカー統合による機械学習ベースの認知症分類",
  "original_title": "Multidomain Electroencephalography Biomarker Fusion for Machine Learning-Based Dementia Classification.",
  "authors": [
    "Thomas J",
    "Subhashree S",
    "Mohanty SN",
    "V S DP",
    "Sanjesh R",
    "Jibrin Musa M"
  ],
  "journal": "Journal of visualized experiments : JoVE",
  "published_date": "2026-09-25",
  "online_publication_date": "2026-09-25",
  "sort_date": "2026-09-25",
  "generated_at": "2026-09-27T23:28:26+00:00",
  "updated_at": "2026-09-27T23:28:26+00:00",
  "doi": "10.3791/72549",
  "pmid": "42801300",
  "source_url": "https://doi.org/10.3791/72549",
  "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/42801300/",
  "slug": "multidomain-electroencephalography-biomarker-fusion-for-machine-learning-based-d",
  "url_path": "/articles/2026/09/multidomain-electroencephalography-biomarker-fusion-for-machine-learning-based-d/",
  "categories": [
    "認知症",
    "神経疾患",
    "認知機能"
  ],
  "score": {
    "clinical_importance": 3.0,
    "novelty": 2.0,
    "usefulness": 3.0,
    "design_strength": 2.0,
    "reader_interest": 2.0,
    "total_score": 12.0,
    "categories": [
      "認知症",
      "神経疾患",
      "認知機能"
    ],
    "reason": "公開EEGデータセット(AD36名、FTD23名、健常29名)を用い、RMS・PSD・エントロピーなど多領域特徴量とランダムフォレストで認知症分類を試みた機械学習手法論文。explainable AIとablation解析により特徴量寄与を検討している点は方法論的に丁寧だが、サンプル数が小さく既存の公開データを用いた再解析であり、外部検証や臨床応用への言及もない。JoVEというビデオ実験手法誌の性質上、技術的再現性の提示が主目的であり、臨床的novelty・重要性は限定的である。"
  },
  "summary": "公開EEGデータセットを用い、複数領域の脳波特徴量とランダムフォレストによりアルツハイマー病・前頭側頭型認知症・健常者を分類する手法を検討した研究。",
  "background": "脳波(EEG)は非侵襲的に脳活動を評価できる手法として、神経変性疾患の特徴づけに応用が検討されてきました。本研究では、複数の領域から抽出したEEGバイオマーカーを組み合わせることで、アルツハイマー病(AD)、前頭側頭型認知症(FTD)、健常者(HC)を機械学習によって識別できるかを検証しています。",
  "participants": "公開されている安静時・閉眼状態のEEG記録データセットを使用し、AD群36名、FTD群23名、健常対照群29名の計88名が含まれています。",
  "methods": "各参加者のEEG記録から、二乗平均平方根(RMS)、パワースペクトル密度(PSD)、エントロピー指標などの多領域特徴量と人口統計学的特徴を抽出しました。これらを組み合わせた特徴量セットを用いてランダムフォレスト分類器を学習させ、説明可能AI(explainable AI)により特徴量の解釈を行いました。さらに、特徴量の安定性評価とCohenのd効果量分析により各特徴量の寄与を検討し、続いてアブレーション解析(特定の特徴量を除いた際の性能変化の検討)を実施しました。",
  "results": "エントロピー系の特徴量は分類への寄与が最も低いことが示されました。全ての多領域特徴量を用いたモデルでは、学習データで96%、テストデータで92%の分類精度が得られました。エントロピー特徴量を除外すると、テストデータの精度は94%に向上しました。",
  "clinical_meaning": "本研究は、複数のEEG特徴量領域を組み合わせることで認知症関連疾患の分類に有用な情報が得られる可能性を示す技術的検討であり、将来的な非侵襲的補助評価手法の開発に向けた基礎的知見を提供するものです。ただし、実際の臨床診断プロセスへの適用を裏付けるものではありません。",
  "limitations": [
    "公開データセットの再解析であり、対象者数が比較的少数(計88名)である点",
    "外部データセットや異なる施設での検証が行われていない",
    "実際の臨床現場における診断精度や有用性については検討されていない"
  ],
  "disclaimer": "本記事は論文の書誌情報および抄録を基にAIを利用して作成した要約です。診断・治療等の医学的助言を目的とするものではありません。詳細は原著論文をご確認ください。"
}
---

# 多領域脳波バイオマーカー統合による機械学習ベースの認知症分類

**Original title:** Multidomain Electroencephalography Biomarker Fusion for Machine Learning-Based Dementia Classification.

## 原著論文

- Original title: Multidomain Electroencephalography Biomarker Fusion for Machine Learning-Based Dementia Classification.
- 著者: Thomas J, Subhashree S, Mohanty SN, V S DP, Sanjesh R, Jibrin Musa M
- 雑誌名: Journal of visualized experiments : JoVE
- 公開日: 2026-09-25
- 発行日: 2026-09-25
- DOI: 10.3791/72549
- PMID: 42801300
- 原著論文へのリンク: https://doi.org/10.3791/72549

## 概要

公開EEGデータセットを用い、複数領域の脳波特徴量とランダムフォレストによりアルツハイマー病・前頭側頭型認知症・健常者を分類する手法を検討した研究。

## 背景・目的

脳波(EEG)は非侵襲的に脳活動を評価できる手法として、神経変性疾患の特徴づけに応用が検討されてきました。本研究では、複数の領域から抽出したEEGバイオマーカーを組み合わせることで、アルツハイマー病(AD)、前頭側頭型認知症(FTD)、健常者(HC)を機械学習によって識別できるかを検証しています。

## 対象

公開されている安静時・閉眼状態のEEG記録データセットを使用し、AD群36名、FTD群23名、健常対照群29名の計88名が含まれています。


## 方法

各参加者のEEG記録から、二乗平均平方根(RMS)、パワースペクトル密度(PSD)、エントロピー指標などの多領域特徴量と人口統計学的特徴を抽出しました。これらを組み合わせた特徴量セットを用いてランダムフォレスト分類器を学習させ、説明可能AI(explainable AI)により特徴量の解釈を行いました。さらに、特徴量の安定性評価とCohenのd効果量分析により各特徴量の寄与を検討し、続いてアブレーション解析(特定の特徴量を除いた際の性能変化の検討)を実施しました。

## 結果

エントロピー系の特徴量は分類への寄与が最も低いことが示されました。全ての多領域特徴量を用いたモデルでは、学習データで96%、テストデータで92%の分類精度が得られました。エントロピー特徴量を除外すると、テストデータの精度は94%に向上しました。

## 臨床的示唆

本研究は、複数のEEG特徴量領域を組み合わせることで認知症関連疾患の分類に有用な情報が得られる可能性を示す技術的検討であり、将来的な非侵襲的補助評価手法の開発に向けた基礎的知見を提供するものです。ただし、実際の臨床診断プロセスへの適用を裏付けるものではありません。

## 限界

- 公開データセットの再解析であり、対象者数が比較的少数(計88名)である点
- 外部データセットや異なる施設での検証が行われていない
- 実際の臨床現場における診断精度や有用性については検討されていない

## 原著論文を確認する

https://doi.org/10.3791/72549

本記事は論文の書誌情報および抄録を基にAIを利用して作成した要約です。診断・治療等の医学的助言を目的とするものではありません。詳細は原著論文をご確認ください。
