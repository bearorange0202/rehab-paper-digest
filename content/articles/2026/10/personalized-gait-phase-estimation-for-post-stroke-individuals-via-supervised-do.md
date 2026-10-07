---
{
  "title": "限られた歩行データを用いた教師ありドメイン適応による脳卒中後個別化歩行位相推定",
  "original_title": "Personalized Gait Phase Estimation for Post-Stroke Individuals via Supervised Domain Adaptation with Limited Gait Data.",
  "authors": [
    "Choi S",
    "Kong K"
  ],
  "journal": "IEEE transactions on neural systems and rehabilitation engineering : a publication of the IEEE Engineering in Medicine and Biology Society",
  "published_date": "2026-10-06",
  "online_publication_date": "2026-10-06",
  "sort_date": "2026-10-06",
  "generated_at": "2026-10-07T00:13:51+00:00",
  "updated_at": "2026-10-07T00:13:51+00:00",
  "doi": "10.1109/TNSRE.2026.3740500",
  "pmid": "42837236",
  "source_url": "https://doi.org/10.1109/TNSRE.2026.3740500",
  "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/42837236/",
  "slug": "personalized-gait-phase-estimation-for-post-stroke-individuals-via-supervised-do",
  "url_path": "/articles/2026/10/personalized-gait-phase-estimation-for-post-stroke-individuals-via-supervised-do/",
  "categories": [
    "歩行",
    "脳卒中",
    "福祉用具・支援技術"
  ],
  "score": {
    "clinical_importance": 3.0,
    "novelty": 4.0,
    "usefulness": 3.0,
    "design_strength": 3.0,
    "reader_interest": 3.0,
    "total_score": 16.0,
    "categories": [
      "歩行",
      "脳卒中",
      "福祉用具・支援技術"
    ],
    "reason": "脳卒中後歩行の歩行位相推定を、非障害者データと限られた患者データを用いた教師ありドメイン適応(MP-MMD)で個別化する手法を提案。7名の少数例によるLeave-One-Trial-Out評価で既存手法より誤差が有意に低減したことを示す概念実証研究で、工学的新規性はあるが臨床応用や被験者数の面では限定的。"
  },
  "summary": "非障害者データと少数の患者本人データを組み合わせたドメイン適応手法により、脳卒中後の歩行位相推定の個別化精度を向上させた概念実証研究。",
  "background": "歩行位相の正確な推定は、歩行分析やリハビリテーション、神経補装具、ウェアラブル支援機器において歩行周期に応じたモニタリングや介入を可能にするために重要とされています。しかし脳卒中後の病的歩行は個人差が大きい一方で、患者本人の歩行データは限られることが多く、個別化された推定モデルの構築が課題となっていました。",
  "participants": "脳卒中後の歩行に関する参加者7名のデータを用いた評価が行われています。あわせて、モデル構築には非障害者の歩行データも使用されています。",
  "methods": "本研究では、立脚相と遊脚相を分けて潜在特徴を揃える多相最大平均差(MP-MMD)を目的関数とした教師ありドメイン適応(SDA)フレームワークを提案しています。共有の特徴抽出器とドメイン別の回帰器を、非障害者データと各患者の限られたラベル付きデータを用いて共同学習し、被験者ごとの個別モデルを構築しました。評価にはLeave-One-Trial-Out法を用い、提案手法と、Source Only、Target Only、Fine-Tuning、通常のグローバルMMDといった比較手法との性能を比較しています。",
  "results": "提案したSDA手法は、7名の参加者においてRMSE 4.37±1.26%、最大絶対誤差(MaxAE) 8.64±1.90%を達成しました。Holm補正後、提案手法はSource OnlyおよびFine-TuningよりRMSEが有意に低く、3つの比較手法すべてよりMaxAEが有意に低い結果でした(いずれも補正後p=0.047)。Target OnlyおよびFine-Tuningと比較すると、RMSEはそれぞれ13.32%、57.51%、MaxAEは26.50%、72.17%の数値上の減少が見られました。また、従来のグローバルMMDと比較して、MP-MMDはRMSEで2.87%、MaxAEで2.77%の数値上の改善を示しました。",
  "clinical_meaning": "本研究は、脳卒中後の歩行位相推定を、限られた患者データのみでも非障害者データとの組み合わせにより個別化できる可能性を示すデータ効率の高い手法の概念実証として位置づけられます。将来的にウェアラブル機器や神経補装具における歩行位相依存の制御・モニタリングへの応用が期待される基礎的知見です。",
  "limitations": [
    "評価対象が7名と少数であり、概念実証段階の結果である点に留意が必要です",
    "Leave-One-Trial-Out評価であり、実際の臨床場面での汎化性能や長期的な妥当性は確認されていません"
  ],
  "disclaimer": "本記事は論文の書誌情報および抄録を基にAIを利用して作成した要約です。診断・治療等の医学的助言を目的とするものではありません。詳細は原著論文をご確認ください。"
}
---

# 限られた歩行データを用いた教師ありドメイン適応による脳卒中後個別化歩行位相推定

**Original title:** Personalized Gait Phase Estimation for Post-Stroke Individuals via Supervised Domain Adaptation with Limited Gait Data.

## 原著論文

- Original title: Personalized Gait Phase Estimation for Post-Stroke Individuals via Supervised Domain Adaptation with Limited Gait Data.
- 著者: Choi S, Kong K
- 雑誌名: IEEE transactions on neural systems and rehabilitation engineering : a publication of the IEEE Engineering in Medicine and Biology Society
- 公開日: 2026-10-06
- 発行日: 2026-10-06
- DOI: 10.1109/TNSRE.2026.3740500
- PMID: 42837236
- 原著論文へのリンク: https://doi.org/10.1109/TNSRE.2026.3740500

## 概要

非障害者データと少数の患者本人データを組み合わせたドメイン適応手法により、脳卒中後の歩行位相推定の個別化精度を向上させた概念実証研究。

## 背景・目的

歩行位相の正確な推定は、歩行分析やリハビリテーション、神経補装具、ウェアラブル支援機器において歩行周期に応じたモニタリングや介入を可能にするために重要とされています。しかし脳卒中後の病的歩行は個人差が大きい一方で、患者本人の歩行データは限られることが多く、個別化された推定モデルの構築が課題となっていました。

## 対象

脳卒中後の歩行に関する参加者7名のデータを用いた評価が行われています。あわせて、モデル構築には非障害者の歩行データも使用されています。


## 方法

本研究では、立脚相と遊脚相を分けて潜在特徴を揃える多相最大平均差(MP-MMD)を目的関数とした教師ありドメイン適応(SDA)フレームワークを提案しています。共有の特徴抽出器とドメイン別の回帰器を、非障害者データと各患者の限られたラベル付きデータを用いて共同学習し、被験者ごとの個別モデルを構築しました。評価にはLeave-One-Trial-Out法を用い、提案手法と、Source Only、Target Only、Fine-Tuning、通常のグローバルMMDといった比較手法との性能を比較しています。

## 結果

提案したSDA手法は、7名の参加者においてRMSE 4.37±1.26%、最大絶対誤差(MaxAE) 8.64±1.90%を達成しました。Holm補正後、提案手法はSource OnlyおよびFine-TuningよりRMSEが有意に低く、3つの比較手法すべてよりMaxAEが有意に低い結果でした(いずれも補正後p=0.047)。Target OnlyおよびFine-Tuningと比較すると、RMSEはそれぞれ13.32%、57.51%、MaxAEは26.50%、72.17%の数値上の減少が見られました。また、従来のグローバルMMDと比較して、MP-MMDはRMSEで2.87%、MaxAEで2.77%の数値上の改善を示しました。

## 臨床的示唆

本研究は、脳卒中後の歩行位相推定を、限られた患者データのみでも非障害者データとの組み合わせにより個別化できる可能性を示すデータ効率の高い手法の概念実証として位置づけられます。将来的にウェアラブル機器や神経補装具における歩行位相依存の制御・モニタリングへの応用が期待される基礎的知見です。

## 限界

- 評価対象が7名と少数であり、概念実証段階の結果である点に留意が必要です
- Leave-One-Trial-Out評価であり、実際の臨床場面での汎化性能や長期的な妥当性は確認されていません

## 原著論文を確認する

https://doi.org/10.1109/TNSRE.2026.3740500

本記事は論文の書誌情報および抄録を基にAIを利用して作成した要約です。診断・治療等の医学的助言を目的とするものではありません。詳細は原著論文をご確認ください。
