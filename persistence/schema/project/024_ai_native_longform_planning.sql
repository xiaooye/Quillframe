CREATE TABLE planning_contract_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  release TEXT NOT NULL CHECK(release = 'ai-native-longform-v2')
);

INSERT INTO planning_contract_identity(singleton, release)
VALUES(1, 'ai-native-longform-v2');
