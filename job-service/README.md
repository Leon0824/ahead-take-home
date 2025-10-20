# Ahead Job Service

## 結構

api-service 建立 job 時會在資料庫生成一筆紀錄，記下 job ID、用戶 ID、參數、狀態、結果等資訊，job-service 在處理 job 期間會更新資料庫之 job 紀錄。

主要程式碼位於 ./jobs/ 內，主要 job 處理函式在 ./jobs/main.py，目前有：

- Files stat job：統計單一用戶所有上傳檔案之數量與總大小。
- FCS info job：讀取指定 FCS 檔案，取得部分資訊。

## 開發環境建置

1. 安裝虛擬環境和套件管理工具 PDM。
2. 安裝專案依賴套件。
3. 設置 .env 檔案。
4. 運行開發環境。

### 安裝虛擬環境和套件管理工具 PDM

本專案採用之 Python 虛擬環境與套件管理器為 [PDM](https://github.com/pdm-project/pdm)，請參考 PDM 文件安裝 PDM。

安裝完成後，驗證 PDM 可用與否：

```shell
$ pdm --version

PDM, version 2.26.0
```

若成功出現 PDM 之版次訊息，表示 PDM 安裝完成。

### 安裝專案依賴套件

專案之依賴套件定義於 pyproject.toml 與 pdm.lock 檔案，PDM 會以 pdm.lock 內定義之套件與版次安裝依賴套件，用 PDM 建立虛擬環境與安裝套件之指令如下：

```shell
$ cd ./projects/ahead-take-home/job-service/

$ pdm install
```

執行完成後，專案資料夾內會有 .venv/ 子資料夾，此即為 PDM 生成之 Python 虛擬環境與套件所在之資料夾，後續依賴套件之增加移除都靠 PDM 管理，無需人工進入異動。

### 設置 .env 檔案

在專案根目錄下建立 .env 檔案，參考 templates/.env.development 並根據自身開發環境之實際狀況填入每項 .env 變數之值。

### 運行開發環境

運行開發環境之命令如下：

```shell
$ pdm run python -m jobs
```

前導命令 `pdm run` 表示令 PDM 在虛擬環境下執行命令，後面 `python -m jobs` 為運行開發環境之主要指令。

執行後，worker 就會開始跑 job。


## 容器化運行

1. 建構映像
2. 運行容器

### 建構映像

在專案資料夾內執行此命令：

```shell
$ ./scripts/docker-build-development-image.sh
```

此命令會根據 Containerfile 建置映像。

建置完成後，確認映像存在與否：

```shell
$ docker images

REPOSITORY          TAG           IMAGE ID       CREATED        SIZE
ahead-job-service   development   674b6cdb2baf   1 hours ago   471MB
```

應該會看到名為 ahead-job-service:development 之映像。

### 運行容器

容器以 Docker compose 模式運行，請參閱上層 compose 資料夾之文件。
