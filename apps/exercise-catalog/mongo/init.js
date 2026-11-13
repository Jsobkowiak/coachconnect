db = db.getSiblingDB("coachconnect_exercises");
db.createUser({
  user: "catalog",
  pwd: process.env.CATALOG_MONGO_PASSWORD,
  roles: [{ role: "readWrite", db: "coachconnect_exercises" }],
});
