# Rehab Paper Digest 運用手順書

このフォルダは、医学・リハビリテーション領域の新着論文を自動で集め、AIで日本語記事にして、Webサイトとして公開するための一式です。

プログラミングに詳しくない方でも作業できるように、最初にやることだけを順番に書きます。

## まず何をすればいいか

あなたが最初にやることは、この5つです。

1. GitHubアカウントを用意する
2. GitHubに新しいリポジトリを作る
3. このフォルダの中身をGitHubへ入れる
4. Claude APIキーをGitHub Secretsに登録する
5. GitHub PagesとGitHub Actionsを確認して、手動テストする

難しく見えますが、やることは「GitHubの画面でクリックして設定する」作業がほとんどです。

## この仕組みで使うもの

### GitHub

作ったファイルを置く場所です。Webサイト公開と毎日の自動実行もGitHub上で行います。

### GitHub Pages

GitHubに置いた `public` フォルダをWebサイトとして公開する機能です。

### GitHub Actions

毎日決まった時間に自動でプログラムを動かす機能です。このプロジェクトでは、日本時間の毎朝6時に論文取得を行います。

### GitHub Secrets

APIキーなど、人に見せてはいけない文字列を安全に保存する場所です。Claude APIキーはここに入れます。コードの中には書きません。

### Claude API

論文のタイトル、書誌情報、抄録をもとに、日本語記事を作るために使います。ここだけ従量課金が発生する可能性があります。

## 作成済みファイルの場所

このプロジェクトの中身は、次のような構成です。

```text
rehab-paper-digest/
├── .github/workflows/daily-update.yml
├── config.yaml
├── content/articles/
├── data/processed_articles.json
├── public/
├── scripts/daily_update.py
├── requirements.txt
└── README.md
```

主に触るのは `config.yaml` と GitHubの設定画面だけです。

## Step 1: GitHubアカウントを用意する

すでにGitHubアカウントがある場合は、このStepは飛ばしてください。

1. ブラウザで [GitHub](https://github.com/) を開きます。
2. `Sign up` をクリックします。
3. メールアドレス、パスワード、ユーザー名を入力します。
4. 画面の案内に従って登録を完了します。

ここで決めたユーザー名は、あとでWebサイトのURLに使います。

例:

```text
https://あなたのユーザー名.github.io/rehab-paper-digest/
```

## Step 2: GitHubに新しいリポジトリを作る

リポジトリとは、このプロジェクトのファイル置き場です。

1. GitHubにログインします。
2. 画面右上の `+` をクリックします。
3. `New repository` をクリックします。
4. `Repository name` に次のように入力します。

```text
rehab-paper-digest
```

5. `Public` または `Private` を選びます。

最初は `Public` の方がGitHub Pages公開で迷いにくいです。

6. `Add a README file` にはチェックを入れないでください。
7. `.gitignore` と `license` も選ばないでください。
8. `Create repository` をクリックします。

これでGitHub上に空の置き場ができます。

## Step 3: config.yamlを書き換える

GitHubにアップロードする前に、サイトURLをあなた用に直します。

このフォルダの中にある `config.yaml` を開いてください。

最初の方に、次のような部分があります。

```yaml
site:
  name: "Rehab Paper Digest"
  description: "医学・リハビリテーション領域の新着論文を、抄録に基づいて医療職向けに読みやすく整理する論文ダイジェストです。"
  url: "https://YOUR_GITHUB_USERNAME.github.io"
  base_path: "/rehab-paper-digest"
```

ここで `YOUR_GITHUB_USERNAME` を、あなたのGitHubユーザー名に変えます。

例として、GitHubユーザー名が `yamada-taro` の場合はこうします。

```yaml
site:
  name: "Rehab Paper Digest"
  description: "医学・リハビリテーション領域の新着論文を、抄録に基づいて医療職向けに読みやすく整理する論文ダイジェストです。"
  url: "https://yamada-taro.github.io"
  base_path: "/rehab-paper-digest"
```

`base_path` はリポジトリ名です。Step 2で `rehab-paper-digest` という名前にしたなら、このままで大丈夫です。

リポジトリ名を変えた場合だけ、`base_path` も変えてください。

例:

```yaml
base_path: "/my-paper-site"
```

## Step 4: ファイルをGitHubへアップロードする

一番簡単な方法を書きます。

1. GitHubで、Step 2で作ったリポジトリを開きます。
2. 画面中央または上部にある `uploading an existing file` をクリックします。
3. この `rehab-paper-digest` フォルダの中身をすべて選択します。
4. GitHubのアップロード画面へドラッグ&ドロップします。

注意してください。アップロードするのは `rehab-paper-digest` フォルダそのものではなく、その中身です。

つまり、GitHub上で次のファイルが一番上に見える状態が正しいです。

```text
config.yaml
requirements.txt
README.md
scripts/
public/
data/
content/
.github/
```

5. 画面下の `Commit changes` という欄までスクロールします。
6. そのまま `Commit changes` をクリックします。

これでファイルがGitHubに入ります。

## Step 5: Claude APIキーを用意する

Claude APIキーは、記事生成に使う秘密の文字列です。

1. [Anthropic Console](https://console.anthropic.com/) を開きます。
2. ログインします。
3. API Keys の画面を開きます。
4. 新しいAPIキーを作成します。
5. 表示されたAPIキーを控えます。

APIキーは他人に見せないでください。GitHubの通常ファイルにも貼らないでください。

## Step 6: GitHub SecretsにClaude APIキーを登録する

ここがかなり大事です。APIキーはGitHub Secretsに入れます。

1. GitHubで対象リポジトリを開きます。
2. 上部メニューの `Settings` をクリックします。
3. 左側メニューの `Secrets and variables` をクリックします。
4. その中の `Actions` をクリックします。
5. `New repository secret` をクリックします。
6. `Name` に次を入力します。

```text
ANTHROPIC_API_KEY
```

7. `Secret` にClaude APIキーを貼り付けます。
8. `Add secret` をクリックします。

これでClaude APIキーの登録は完了です。

任意で、将来NCBI APIキーを使う場合は、同じ画面で次の名前のSecretを追加します。

```text
NCBI_API_KEY
```

ただし、これは必須ではありません。なくてもPubMed取得は動きます。

## Step 7: GitHub Actionsを有効にする

GitHub Actionsは、自動実行の仕組みです。

1. GitHubで対象リポジトリを開きます。
2. 上部メニューの `Actions` をクリックします。
3. 初回だけ確認画面が出ることがあります。
4. `I understand my workflows, go ahead and enable them` のようなボタンが出たらクリックします。
5. 左側に `Daily paper update` が表示されていればOKです。

この設定により、毎日自動で論文取得が動きます。

## Step 8: GitHub Pagesを有効にする

Webサイトを公開する設定です。

1. GitHubで対象リポジトリを開きます。
2. 上部メニューの `Settings` をクリックします。
3. 左側メニューの `Pages` をクリックします。
4. `Build and deployment` という項目を探します。
5. `Source` を `GitHub Actions` にします。
6. 保存ボタンが出た場合は保存します。

このプロジェクトでは、GitHub Actionsが `public` フォルダを公開します。

## Step 9: まず安全な手動テストをする

いきなり本番実行せず、まずはClaude APIを使わないテストをします。これならClaude API料金はかかりません。

1. GitHubで対象リポジトリを開きます。
2. 上部メニューの `Actions` をクリックします。
3. 左側の `Daily paper update` をクリックします。
4. 右側の `Run workflow` をクリックします。
5. `dry_run` をオンにします。
6. `no_claude` もオンにします。
7. `Run workflow` をクリックします。

このテストでは次のことだけ確認します。

- PubMedから論文を取得できるか
- リハビリテーション関連の候補を選べるか
- 重複や抄録なし論文を除外できるか

記事作成、GitHubへの自動commit、Web公開は行いません。

## Step 10: ログを確認する

手動テストを実行したら、ログを見ます。

1. `Actions` タブを開きます。
2. 実行中または完了した `Daily paper update` をクリックします。
3. `update` をクリックします。
4. `Run daily update` を開きます。

成功している場合、次のようなログが出ます。

```text
[daily-update] fetched_pmids=100
[daily-update] fetched_details=100 candidates=84 excluded=...
[daily-update] Claude disabled: heuristic candidate scoring only
[daily-update] claude_evaluations=12 selected=8 api_errors=0
```

意味は次の通りです。

- `fetched_pmids`: PubMedから見つけた論文数
- `fetched_details`: 詳細情報を取得できた論文数
- `candidates`: 記事化候補になった論文数
- `excluded`: 除外された論文の内訳
- `selected`: 掲載候補に選ばれた論文数
- `api_errors`: APIエラー数

## Step 11: Claudeを使った本番実行をする

安全なテストが成功したら、本番に近い実行をします。

1. `Actions` タブを開きます。
2. 左側の `Daily paper update` をクリックします。
3. `Run workflow` をクリックします。
4. `dry_run` をオフにします。
5. `no_claude` をオフにします。
6. `Run workflow` をクリックします。

この実行では、Claude APIを使って記事を生成します。

成功すると、GitHub上に次のような変更が自動で追加されます。

```text
content/articles/
data/processed_articles.json
public/
```

さらにGitHub Pagesへ公開されます。

## Step 12: 公開されたWebサイトを見る

GitHub Pagesの公開URLは通常この形です。

```text
https://あなたのGitHubユーザー名.github.io/rehab-paper-digest/
```

GitHubの画面から確認する場合は、次の手順です。

1. リポジトリの `Settings` を開きます。
2. 左側の `Pages` をクリックします。
3. 公開が完了していれば、公開URLが表示されます。
4. そのURLをクリックします。

最初の公開には数分かかることがあります。

## Step 13: 毎日の自動実行について

このプロジェクトは、毎日日本時間の朝6時に自動実行されます。

設定は `.github/workflows/daily-update.yml` にあります。

```yaml
- cron: "0 21 * * *"
```

GitHub Actionsの時刻はUTCです。日本時間はUTCより9時間進んでいるので、`21:00 UTC` が日本時間の翌朝 `06:00 JST` になります。

## 普段変更する場所

普段は `config.yaml` だけ見れば大丈夫です。

### サイト名を変える

```yaml
site:
  name: "Rehab Paper Digest"
```

### サイト説明を変える

```yaml
site:
  description: "医学・リハビリテーション領域の新着論文を..."
```

### 1日に作る記事数を変える

```yaml
site:
  max_articles_per_day: 8
```

たとえば1日5本までにしたい場合は、こうします。

```yaml
max_articles_per_day: 5
```

### PubMed検索式を変える

```yaml
pubmed:
  search_query: >
    (
      "occupational therapy"[Title/Abstract]
      OR "physical therapy"[Title/Abstract]
      OR rehabilitation[Title/Abstract]
    )
```

検索対象を増やしたい場合は、`OR` でキーワードを追加します。

### Claude APIの使いすぎを防ぐ

```yaml
claude:
  max_api_calls_per_day: 20
  max_evaluation_candidates: 12
```

API料金が心配な場合は、小さめにしてください。

例:

```yaml
max_api_calls_per_day: 10
max_evaluation_candidates: 6
```

## 記事はどこに作られるか

生成された記事のMarkdownはここに入ります。

```text
content/articles/
```

Web公開用のHTMLはここに作られます。

```text
public/
```

掲載済み論文の記録はここに入ります。

```text
data/processed_articles.json
```

この `processed_articles.json` は重要です。削除すると、過去に掲載した論文をもう一度記事化する可能性があります。

## 絶対にやってはいけないこと

### APIキーをファイルに書かない

次のようなことはしないでください。

```text
ANTHROPIC_API_KEY=sk-ant-...
```

APIキーは必ずGitHub Secretsに入れます。

### data/processed_articles.jsonを消さない

重複防止に使っています。

### 生成された記事を医学的助言として使わない

このサイトの記事は、論文抄録に基づく要約です。診断、治療、臨床判断の根拠として単独で使うものではありません。

## よくあるトラブル

### Actionsが赤く失敗した

まずログを見ます。

1. `Actions` タブを開きます。
2. 失敗した実行をクリックします。
3. `update` をクリックします。
4. 赤くなっている項目を開きます。

よくある原因は次のどれかです。

- `ANTHROPIC_API_KEY` が登録されていない
- `config.yaml` の書き方が崩れている
- Claude APIの残高や利用制限に引っかかっている
- PubMedや外部APIが一時的に不安定

### ANTHROPIC_API_KEY がないと言われる

GitHub Secretsの登録名を確認してください。

正しい名前はこれです。

```text
ANTHROPIC_API_KEY
```

小文字や余計なスペースが入ると認識されません。

### サイトの見た目が崩れる

`config.yaml` の `base_path` がリポジトリ名と一致しているか確認してください。

リポジトリ名が `rehab-paper-digest` なら、こうです。

```yaml
base_path: "/rehab-paper-digest"
```

### 記事が増えない

次の可能性があります。

- 条件に合う新着論文が少ない
- 抄録がない論文が多い
- すでに掲載済みだった
- Claudeの評価で掲載価値スコアが基準未満だった

無理に記事数を増やさない設計にしています。

### Claude API料金が心配

`config.yaml` のこの部分を小さくしてください。

```yaml
claude:
  max_api_calls_per_day: 10
  max_evaluation_candidates: 6
```

さらに、手動テストでは必ず `dry_run` と `no_claude` をオンにしてください。

## このプロジェクトで守っている安全方針

- 論文本文を転載しない
- PubMedから取れる書誌情報と抄録を中心に使う
- 抄録にない情報をAIに推測させない
- 存在しない対象者数、結果、統計値を書かせない
- 因果関係を断定しすぎない
- 医学的助言として書かない
- 原著論文へのリンクを必ず載せる
- 同じ論文を重複掲載しない
- APIキーをコードやログに出さない

## ローカルで試したい場合

GitHubではなく自分のパソコンで試したい場合の手順です。分からなければ、この章は飛ばして大丈夫です。

```bash
python -m pip install -r requirements.txt
python scripts/daily_update.py --dry-run --no-claude
```

Claude APIを使う場合は、環境変数を設定してから実行します。

Windows PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="あなたのClaude APIキー"
python scripts/daily_update.py
```

Mac/Linux:

```bash
export ANTHROPIC_API_KEY="あなたのClaude APIキー"
python scripts/daily_update.py
```

## 参考リンク

- [GitHub ActionsでSecretsを使う公式ドキュメント](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions)
- [GitHub Pages公式ドキュメント](https://docs.github.com/pages)
- [GitHub Actionsを手動実行する公式ドキュメント](https://docs.github.com/actions/managing-workflow-runs/manually-running-a-workflow)
- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [NCBI E-Utilities Quick Start](https://eutilities.github.io/site/Quick_Start/eu_quick/)
