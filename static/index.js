"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const genKey = document.querySelector(".generate-key-btn");
  const keyContent = document.querySelector(".key");
  const quote = document.querySelector(".quote");
  const logout = document.querySelector(".logout");
  if (genKey) {
    keyContent.style.display = "none";
    genKey.onclick = () => {
      console.log("gen key");
      fetch("/getquote", {
        headers: { "Content-Type": "application/json" },
        method: "post",
        body: JSON.stringify({
          key: keyContent.innerHTML,
        }),
      })
        .then((res) => res.json())
        .then((result) => {
          console.log(result);
          quote.innerHTML = `""${result.quote.quote}""`;
        })
        .catch((err) => console.log(err));
    };
  }

  logout.onclick = () => {
    document.cookie =
      "account_user=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    location.reload();
  };
});
