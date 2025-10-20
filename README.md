# Ahead Take-Home Project


## 專案結構

主要服務：

- api-service：負責與前端通信。
- job-service：負責跑 job queue。

其他使用既有映像之服務：

- PostgreSQL：資料庫。
- Redis：Job queue 後端。
- Traefik：Web server 與反向代理。

## 開發環境建置

服務間解耦，可獨立開發，獨立測試，主要服務開發環境建置與開發說明參見子專案內之 README 文件。

## 容器化運行

1. 建構映像
2. 配置環境變數
3. 運行容器
4. 整合測試

### 建構映像

主要服務之映像建置參照子專案內之 README 文件。

其他資料庫等周邊服務使用現成映像。

### 配置環境變數

在專案根目錄下建立 .env 檔案，參考 templates/.env.development 並根據自身開發環境之實際狀況填入每項 .env 變數之值。

### 運行容器

執行以下命令運行 compose：

```shell
$ cd ./projects/ahead-take-home/
$ docker compose up --detach
```

終止運行：

```shell
$ cd ./projects/ahead-take-home/
$ docker compose down
```

### 整合測試

整合測試位於 compose 專案之 /tests/ 資料夾內。

整合測試會自行啟動 compose，無需事先手動跑 compose。

執行整合測試：

```shell
$ cd ./tests/
$ pdm run pytest
```
