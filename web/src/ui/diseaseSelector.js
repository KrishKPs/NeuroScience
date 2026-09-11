const DISEASE_LABELS = {
  parkinsons: "Parkinson's",
  schizophrenia: "Schizophrenia",
  alzheimers: "Alzheimer's",
};

export function setupDiseaseSelector(container, defaultDisease, onChange) {
  container.classList.add("panel");
  container.innerHTML = `<h3>Disease</h3><div id="disease-buttons"></div>`;
  const buttonsEl = container.querySelector("#disease-buttons");

  for (const [key, label] of Object.entries(DISEASE_LABELS)) {
    const btn = document.createElement("button");
    btn.className = "disease-btn" + (key === defaultDisease ? " active" : "");
    btn.textContent = label;
    btn.dataset.disease = key;
    btn.addEventListener("click", () => {
      for (const b of buttonsEl.querySelectorAll(".disease-btn")) b.classList.remove("active");
      btn.classList.add("active");
      onChange(key);
    });
    buttonsEl.appendChild(btn);
  }
}
