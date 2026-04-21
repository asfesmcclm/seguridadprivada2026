document.addEventListener('DOMContentLoaded', () => {
    const appContainer = document.getElementById('app');
    const searchInput = document.getElementById('searchInput');
    let convenioData = null;

    lucide.createIcons();

    // Cargamos el archivo JSON que ya tienes generado
    fetch('convenio_seguridad_privada.json')
        .then(response => response.json())
        .then(data => {
            convenioData = data;
            renderConvenio(data.capitulos);
            if(document.getElementById('loading')) document.getElementById('loading').remove();
        })
        .catch(err => {
            appContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700 rounded-lg">Error: No se encontró el archivo JSON.</div>`;
        });

    function renderConvenio(capitulos) {
        appContainer.innerHTML = '';
        if (capitulos.length === 0) {
            appContainer.innerHTML = '<p class="text-center py-10 text-slate-500">No se han encontrado resultados.</p>';
            return;
        }
        
        capitulos.forEach((cap, index) => {
            const capDiv = document.createElement('div');
            capDiv.className = 'mb-4 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden';
            
            capDiv.innerHTML = `
                <div class="p-4 bg-slate-50 flex justify-between items-center cursor-pointer hover:bg-slate-100 transition-colors" onclick="toggleAccordion('cap-${index}')">
                    <span class="font-bold text-slate-700 pr-4 uppercase text-sm">Capítulo ${cap.num}: ${cap.titulo}</span>
                    <i data-lucide="chevron-down" id="icon-cap-${index}" class="text-slate-400 shrink-0"></i>
                </div>
                <div id="cap-${index}" class="accordion-content">
                    <div class="p-2 divide-y divide-slate-100">
                        ${cap.articulos.map(art => `
                            <div class="p-4 hover:bg-blue-50/30 transition-colors">
                                <h4 class="font-bold text-blue-600 text-sm mb-2">Art. ${art.num}. ${art.titulo}</h4>
                                <div class="text-slate-600 text-sm leading-relaxed">${art.contenido.replace(/\n/g, '<br>')}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            appContainer.appendChild(capDiv);
        });
        lucide.createIcons();
    }

    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase().trim();
        if (!term) {
            renderConvenio(convenioData.capitulos);
            return;
        }

        const filtered = [];
        convenioData.capitulos.forEach(cap => {
            const matches = cap.articulos.filter(art => 
                art.num.toString().toLowerCase().includes(term) || 
                art.titulo.toLowerCase().includes(term) || 
                art.contenido.toLowerCase().includes(term)
            );
            if (matches.length > 0) {
                filtered.push({ ...cap, articulos: matches });
            }
        });

        renderConvenio(filtered);
        document.querySelectorAll('.accordion-content').forEach(el => el.classList.add('open'));
    });
});

function toggleAccordion(id) {
    const content = document.getElementById(id);
    const icon = document.getElementById('icon-' + id);
    const isOpen = content.classList.toggle('open');
    icon.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
}
