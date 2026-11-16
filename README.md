# SGI TECBA – Sistema de Gestión Inteligente (Habilitación Inteligente)
 
**Despliegue actual (Vercel):** [habilitacioninteligente.vercel.app](https://habilitacioninteligente.vercel.app/)]

---

## 1. Stack Tecnológico (Front-end)
El desarrollo del lado del cliente prioriza alto rendimiento, modularidad y cumplimiento de los estándares oficiales del gobierno local:

* **Front-end:** React (`v19.2.8`) y Vite (`v8.3.0`).
* **Estilos y Sistema de Diseño:** Tailwind CSS (`v3.4.19`) combinado con la librería oficial **Obelisco V2** (`@gcba/obelisco-v2: v1.19.0`).
* **Geolocalización y Mapas:** Integración avanzada de **MapLibre GL** con capas satelitales **Esri 3D**, permitiendo la visualización tridimensional de manzanas y parcelas sobre la trama urbana de CABA.
* **Control de Versiones:** Git / GitHub para el flujo de trabajo en ramas colaborativas.

---

## 2. Componentes Principales y su Funcionalidad

* **`App.jsx`**: Componente raíz de la aplicación. Gestiona el enrutamiento interno mediante hash (`window.location.hash`), administra los estados globales de búsqueda y coordina la renderización de las vistas principales (`/`, `/rubros`, `/cobertura`, `/fuentes`).
* **`Navbar.jsx`**: Barra de navegación superior basada en Obelisco V2. Integra los enlaces de las secciones.
* **`ConsultaJourney.jsx`**: El punto central del flujo de consulta. Controla la transición visual entre la pantalla de resultados generales y el circuito detallado de trámites.
* **`ResultPanel.jsx`**: Panel encargado de estructurar y mostrar la información catastral y territorial obtenida (comuna, barrio, superficie, nomenclatura SMP, código urbanístico y fuentes).
* **`TramitesView.jsx`**: Vista dedicada al journey completo de trámites. Muestra los pasos secuenciales y la documentación obligatoria exigida para la habilitación de actividades.
* **`MapView.jsx`**: Componente de cartografía interactiva basado en MapLibre y capas satelitales 3D para la geolocalización precisa de parcelas en CABA.
* **Vistas Secundarias (`RubrosView`, `CoberturaView`, `FuentesView`)**: Módulos informativos estáticos y dinámicos accesibles desde la barra de navegación superior.
