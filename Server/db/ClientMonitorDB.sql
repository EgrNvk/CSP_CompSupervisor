CREATE DATABASE ClientMonitorDB;

USE ClientMonitorDB;

CREATE TABLE clients (
    id         INT IDENTITY(1,1) PRIMARY KEY,
    ip         VARCHAR(45) NOT NULL UNIQUE,
    hostname   NVARCHAR(255) NOT NULL DEFAULT '',
    status     VARCHAR(20) NOT NULL DEFAULT 'Unknown',
    first_seen DATETIME,
    last_seen  DATETIME,
    CONSTRAINT CK_clients_status
        CHECK (status IN ('Online', 'Offline', 'Unknown'))
);

SELECT * FROM clients