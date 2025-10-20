# Ahead API Service


## 開發環境建置

1. 安裝虛擬環境和套件管理工具 PDM。
2. 安裝專案依賴套件。
3. 設置 .env 檔案。
4. 運行開發環境。
5. 異動資料庫 schema。

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
$ cd ./protjects/ahead-take-home/

$ pdm install
```

執行完成後，專案資料夾內會有 .venv/ 子資料夾，此即為 PDM 生成之 Python 虛擬環境與套件所在之資料夾，後續依賴套件之增加移除都靠 PDM 管理，無需人工進入異動。

### 設置 .env 檔案

在專案根目錄下建立 .env 檔案，參考 templates/.env.development 並根據自身開發環境之實際狀況填入每項 .env 變數之值。

### 運行開發環境

運行開發環境之命令執行後之訊息節錄如下：

```shell
$ pdm run fastapi dev

FastAPI   Starting development server 🚀
...
server   Server started at http://127.0.0.1:8000
server   Documentation at http://127.0.0.1:8000/docs
...
INFO   Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
...
INFO   Application startup complete.
```

前導命令 `pdm run` 表示令 PDM 在虛擬環境下執行命令，後面 `fastapi dev` 為運行開發環境之主要指令。

根據訊息提示：

- 開發環境網址為 http://127.0.0.1:8000
- API 文件網址為 http://127.0.0.1:8000/docs
- 按 CTRL+C 可終止程式。

於 `fastapi dev` 模式下，專案資料夾內之檔案異動後 FastAPI 會自動重載，無需頻繁手動終止再運行。

### 異動資料庫 schema

1. 終止程式。
2. 根據需求修改 app/db.py。
3. 執行 `pdm run alembic revision -m 'MESSAGE' --autogenerate`，產生異動腳本。
4. 去 app/alembic/versions/ 找到剛出生的異動腳本，檢查視需要修正。
5. 執行 `pdm run alembic upgrade head` 去真正修改資料庫 schema。


## 測試

pytest 測試腳本位於 ./app/tests/，執行測試命令：

```shell
$ pdm run pytest
```

此命令會執行全部測試腳本，並輸出測試報告。


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
ahead-take-home     development   674b6cdb2baf   1 hours ago   471MB
```

應該會看到名為 ahead-take-home:development 之映像。

### 運行容器

```shell
$ docker compose up --detach
```

