USE master;
GO
IF DB_ID(N'ENV07_DB') IS NOT NULL
BEGIN
    ALTER DATABASE ENV07_DB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE ENV07_DB;
END
GO
CREATE DATABASE ENV07_DB;
GO
USE ENV07_DB;
GO

CREATE TABLE Users (
    UserId       INT IDENTITY(1,1) PRIMARY KEY,
    Username     VARCHAR(50)   NOT NULL UNIQUE,
    FullName     NVARCHAR(100) NOT NULL,
    Salt         VARCHAR(32)   NOT NULL,
    PasswordHash VARCHAR(64)   NOT NULL,
    Role         VARCHAR(10)   NOT NULL DEFAULT 'VIEWER',
    IsActive     BIT           NOT NULL DEFAULT 1,
    CreatedAt    DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_Users_Role CHECK (Role IN ('ADMIN', 'MANAGER', 'FARMER', 'VIEWER'))
);

CREATE TABLE Sessions (
    Token     VARCHAR(64) PRIMARY KEY,
    UserId    INT         NOT NULL REFERENCES Users(UserId),
    CreatedAt DATETIME2   NOT NULL DEFAULT SYSDATETIME(),
    ExpiresAt DATETIME2   NOT NULL
);

CREATE TABLE AppSettings (
    SettingKey   VARCHAR(50)   PRIMARY KEY,
    SettingValue NVARCHAR(500) NOT NULL,
    UpdatedBy    INT           NULL REFERENCES Users(UserId),
    UpdatedAt    DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);

CREATE TABLE Crops (
    CropId      INT IDENTITY(1,1) PRIMARY KEY,
    Name        NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(300) NULL,
    CreatedBy   INT           NULL REFERENCES Users(UserId),
    CreatedAt   DATETIME2     NOT NULL DEFAULT SYSDATETIME()
);

CREATE TABLE CropStages (
    StageId      INT IDENTITY(1,1) PRIMARY KEY,
    CropId       INT           NOT NULL REFERENCES Crops(CropId) ON DELETE CASCADE,
    StageOrder   INT           NOT NULL,
    Name         NVARCHAR(100) NOT NULL,
    DurationDays INT           NOT NULL,
    MoistureMin  DECIMAL(5,2)  NOT NULL,
    MoistureMax  DECIMAL(5,2)  NOT NULL,
    CONSTRAINT UQ_CropStage    UNIQUE (CropId, StageOrder),
    CONSTRAINT CK_Stage_Days   CHECK (DurationDays > 0),
    CONSTRAINT CK_Stage_Range  CHECK (MoistureMin >= 0 AND MoistureMax <= 100 AND MoistureMin < MoistureMax)
);

CREATE TABLE Plantings (
    PlantingId           INT IDENTITY(1,1) PRIMARY KEY,
    CropId               INT           NOT NULL REFERENCES Crops(CropId),
    PlantedDate          DATE          NOT NULL,
    DailyQuotaLiters     DECIMAL(8,2)  NOT NULL,
    MaxLitersPerWatering DECIMAL(8,2)  NOT NULL,
    AutoMode             BIT           NOT NULL DEFAULT 0,
    Status               VARCHAR(10)   NOT NULL DEFAULT 'ACTIVE',
    Note                 NVARCHAR(300) NULL,
    CreatedBy            INT           NULL REFERENCES Users(UserId),
    CreatedAt            DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    EndedAt              DATETIME2     NULL,
    CONSTRAINT CK_Planting_Status CHECK (Status IN ('ACTIVE', 'FINISHED')),
    CONSTRAINT CK_Planting_Quota  CHECK (DailyQuotaLiters >= 0),
    CONSTRAINT CK_Planting_Max    CHECK (MaxLitersPerWatering > 0 AND MaxLitersPerWatering <= DailyQuotaLiters)
);

CREATE TABLE DeviceStatus (
    Id         INT         PRIMARY KEY DEFAULT 1,
    DeviceCode VARCHAR(30) NOT NULL,
    LastSeen   DATETIME2   NOT NULL,
    PumpIsOn   BIT         NOT NULL DEFAULT 0,
    CONSTRAINT CK_Device_One CHECK (Id = 1)
);

CREATE TABLE SensorReadings (
    ReadingId    BIGINT IDENTITY(1,1) PRIMARY KEY,
    ReadAt       DATETIME2    NOT NULL DEFAULT SYSDATETIME(),
    SoilRaw      INT          NULL,
    SoilMoisture DECIMAL(5,2) NOT NULL,
    AirTemp      DECIMAL(5,2) NULL,
    AirHumidity  DECIMAL(5,2) NULL
);

CREATE TABLE Recommendations (
    RecId            INT IDENTITY(1,1) PRIMARY KEY,
    PlantingId       INT           NOT NULL REFERENCES Plantings(PlantingId),
    StageId          INT           NULL REFERENCES CropStages(StageId) ON DELETE SET NULL,
    StageName        NVARCHAR(100) NULL,
    ValidFrom        DATETIME2     NOT NULL,
    ValidTo          DATETIME2     NOT NULL,
    TriggerBelow     DECIMAL(5,2)  NOT NULL,
    MoistureAtCreate DECIMAL(5,2)  NOT NULL,
    TargetMoisture   DECIMAL(5,2)  NULL,
    DurationSec      INT           NOT NULL,
    VolumeLiters     DECIMAL(8,2)  NOT NULL,
    Reason           NVARCHAR(500) NOT NULL,
    ScopeNote        NVARCHAR(300) NOT NULL,
    Status           VARCHAR(12)   NOT NULL DEFAULT 'PROPOSED',
    CreatedBy        INT           NULL REFERENCES Users(UserId),
    CreatedAt        DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    AppliedBy        INT           NULL REFERENCES Users(UserId),
    AppliedAt        DATETIME2     NULL,
    CONSTRAINT CK_Rec_Window   CHECK (ValidFrom < ValidTo),
    CONSTRAINT CK_Rec_Duration CHECK (DurationSec >= 0),
    CONSTRAINT CK_Rec_Volume   CHECK (VolumeLiters >= 0),
    CONSTRAINT CK_Rec_Status   CHECK (Status IN ('PROPOSED', 'OVERRIDDEN', 'APPLIED', 'REJECTED', 'EXPIRED'))
);

CREATE TABLE RecommendationOverrides (
    OverrideId     INT IDENTITY(1,1) PRIMARY KEY,
    RecId          INT           NOT NULL REFERENCES Recommendations(RecId),
    UserId         INT           NOT NULL REFERENCES Users(UserId),
    Action         VARCHAR(10)   NOT NULL,
    OldDurationSec INT           NOT NULL,
    NewDurationSec INT           NULL,
    OldValidTo     DATETIME2     NOT NULL,
    NewValidTo     DATETIME2     NULL,
    Reason         NVARCHAR(500) NOT NULL,
    CreatedAt      DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT CK_Override_Action CHECK (Action IN ('ADJUST', 'REJECT')),
    CONSTRAINT CK_Override_Reason CHECK (LEN(LTRIM(RTRIM(Reason))) >= 10)
);

CREATE TABLE PumpRequests (
    RequestId    INT IDENTITY(1,1) PRIMARY KEY,
    PlantingId   INT           NOT NULL REFERENCES Plantings(PlantingId),
    Liters       DECIMAL(6,2)  NOT NULL,
    DurationSec  INT           NOT NULL,
    Reason       NVARCHAR(500) NOT NULL,
    Status       VARCHAR(10)   NOT NULL DEFAULT 'PENDING',
    RequestedBy  INT           NOT NULL REFERENCES Users(UserId),
    RequestedAt  DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    ReviewedBy   INT           NULL REFERENCES Users(UserId),
    ReviewedAt   DATETIME2     NULL,
    ReviewNote   NVARCHAR(300) NULL,
    CONSTRAINT CK_Request_Liters   CHECK (Liters > 0 AND Liters <= 2),
    CONSTRAINT CK_Request_Duration CHECK (DurationSec > 0 AND DurationSec <= 60),
    CONSTRAINT CK_Request_Reason   CHECK (LEN(LTRIM(RTRIM(Reason))) >= 10),
    CONSTRAINT CK_Request_Status   CHECK (Status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'))
);

CREATE TABLE PumpCommands (
    CommandId      INT IDENTITY(1,1) PRIMARY KEY,
    RecId          INT           NULL REFERENCES Recommendations(RecId),
    RequestId      INT           NULL REFERENCES PumpRequests(RequestId),
    Action         VARCHAR(3)    NOT NULL,
    Source         VARCHAR(15)   NOT NULL,
    DurationSec    INT           NOT NULL DEFAULT 0,
    StopAtMoisture DECIMAL(5,2)  NULL,
    PulseSec       INT           NULL,
    SoakSec        INT           NULL,
    Status         VARCHAR(10)   NOT NULL DEFAULT 'PENDING',
    IssuedBy       INT           NULL REFERENCES Users(UserId),
    CreatedAt      DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    DeliveredAt    DATETIME2     NULL,
    FinishedAt     DATETIME2     NULL,
    PumpedSec      INT           NULL,
    FinalMoisture  DECIMAL(5,2)  NULL,
    StopReason     NVARCHAR(200) NULL,
    CONSTRAINT CK_Pump_Action CHECK (Action IN ('ON', 'OFF')),
    CONSTRAINT CK_Pump_Source CHECK (Source IN ('MANUAL', 'AUTO', 'RECOMMENDATION')),
    CONSTRAINT CK_Pump_Status CHECK (Status IN ('PENDING', 'DELIVERED', 'DONE', 'CANCELLED', 'EXPIRED'))
);

CREATE TABLE IrrigationEvents (
    EventId         INT IDENTITY(1,1) PRIMARY KEY,
    PlantingId      INT           NULL REFERENCES Plantings(PlantingId),
    CommandId       INT           NULL REFERENCES PumpCommands(CommandId),
    RecId           INT           NULL REFERENCES Recommendations(RecId),
    RequestId       INT           NULL REFERENCES PumpRequests(RequestId),
    Source          VARCHAR(15)   NOT NULL,
    StartedAt       DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    DurationSec     INT           NOT NULL,
    EstimatedLiters DECIMAL(8,2)  NOT NULL,
    FinalMoisture   DECIMAL(5,2)  NULL,
    StopReason      NVARCHAR(200) NULL,
    IssuedBy        INT           NULL REFERENCES Users(UserId)
);
GO

CREATE UNIQUE INDEX UX_Plantings_Active ON Plantings(Status) WHERE Status = 'ACTIVE';
CREATE INDEX IX_Readings_Time ON SensorReadings(ReadAt DESC);
CREATE INDEX IX_Events_Time   ON IrrigationEvents(StartedAt DESC);
GO

CREATE OR ALTER VIEW vw_QuotaToday AS
SELECT
    p.PlantingId,
    p.DailyQuotaLiters                           AS LimitLiters,
    ISNULL(u.UsedLiters, 0)                      AS UsedLiters,
    p.DailyQuotaLiters - ISNULL(u.UsedLiters, 0) AS RemainingLiters
FROM Plantings p
OUTER APPLY (
    SELECT SUM(EstimatedLiters) AS UsedLiters
    FROM IrrigationEvents
    WHERE CAST(StartedAt AS DATE) = CAST(GETDATE() AS DATE)
) u
WHERE p.Status = 'ACTIVE';
GO

CREATE OR ALTER VIEW vw_OverrideHistory AS
SELECT o.OverrideId, o.RecId, u.FullName, o.Action,
       o.OldDurationSec, o.NewDurationSec, o.OldValidTo, o.NewValidTo, o.Reason, o.CreatedAt
FROM RecommendationOverrides o
JOIN Users u ON u.UserId = o.UserId;
GO

CREATE OR ALTER VIEW vw_IrrigationLog AS
SELECT e.EventId, e.StartedAt, e.Source, e.DurationSec, e.EstimatedLiters, e.FinalMoisture, e.StopReason,
       e.RecId, e.RequestId, c.Name AS CropName,
       ui.FullName AS IssuedByName,
       ur.FullName AS RequestedByName, uv.FullName AS ReviewedByName, r.Reason AS RequestReason, r.ReviewNote
FROM IrrigationEvents e
LEFT JOIN Plantings pl   ON pl.PlantingId = e.PlantingId
LEFT JOIN Crops c        ON c.CropId = pl.CropId
LEFT JOIN Users ui       ON ui.UserId = e.IssuedBy
LEFT JOIN PumpRequests r ON r.RequestId = e.RequestId
LEFT JOIN Users ur       ON ur.UserId = r.RequestedBy
LEFT JOIN Users uv       ON uv.UserId = r.ReviewedBy;
GO

CREATE OR ALTER PROCEDURE sp_ExpireRecommendations
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE Recommendations
    SET Status = 'EXPIRED'
    WHERE Status IN ('PROPOSED', 'OVERRIDDEN') AND ValidTo < SYSDATETIME();
    DECLARE @n INT = @@ROWCOUNT;

    UPDATE PumpCommands
    SET Status = 'EXPIRED', StopReason = N'ESP32 không nhận lệnh (mất kết nối)'
    WHERE Status = 'PENDING' AND CreatedAt < DATEADD(MINUTE, -2, SYSDATETIME());

    SELECT @n AS ExpiredCount;
END
GO

PRINT N'Đã tạo xong ENV07_DB (13 bảng, 3 view, 1 procedure).';
GO
