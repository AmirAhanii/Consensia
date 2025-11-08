export const nanoid = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";
  let id = "";
  for (let i = 0; i < 21; i += 1) {
    const index = Math.floor(Math.random() * alphabet.length);
    id += alphabet[index];
  }
  return id;
};

