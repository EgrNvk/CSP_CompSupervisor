CREATE DATABASE [ClientMonitorDB];

USE [ClientMonitorDB];

CREATE TABLE [clients] (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [ip] VARCHAR(45)   NOT NULL UNIQUE,
    [hostname] NVARCHAR(255) NOT NULL DEFAULT '',
    [seen] DATETIME,
    [wait_sec] INT,
    status AS (
        CASE
            WHEN DATEADD(SECOND, wait_sec, seen) > GETDATE()
            THEN 'Online'
            ELSE 'Offline'
        END
    )
);

CREATE TABLE [desktop_files] (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [client_id] INT NOT NULL REFERENCES clients(id),
    [name] NVARCHAR(255) NOT NULL,
    [received] DATETIME NOT NULL
);