import type { ActivationStatus, Application } from "./api";
import type { SectionId } from "./components/Layout";

export type StudentJourney = {
  title: string;
  description: string;
  action: SectionId;
  actionLabel: string;
  state: string | null;
  disabled: boolean;
};

type JourneyApplication = Pick<Application, "state" | "placement_state" | "placement_id">;

function journey(
  title: string,
  description: string,
  action: SectionId,
  actionLabel: string,
  state: string | null,
  disabled = false,
): StudentJourney {
  return { title, description, action, actionLabel, state, disabled };
}

export function getStudentJourney(
  application: JourneyApplication | undefined,
  activation: ActivationStatus | undefined,
  loading: boolean,
  applicationsLoaded: boolean,
): StudentJourney {
  if (!application) {
    if (loading) {
      return journey("Consultando tus procesos", "Estamos cargando las postulaciones y prácticas asociadas a tu cuenta.", "applications", "Cargando…", null, true);
    }
    if (!applicationsLoaded) {
      return journey("No se pudo consultar tu proceso", "Revisa el mensaje de error y vuelve a cargar la página para actualizar el estado.", "applications", "Ver mis postulaciones", null);
    }
    return journey("Encuentra una oportunidad para tu práctica", "Explora las oportunidades publicadas y revisa las condiciones de elegibilidad antes de postularte.", "opportunities", "Explorar oportunidades", null);
  }

  const state = application.placement_state ?? application.state;
  switch (application.placement_state) {
    case "ACTIVE":
      return journey("Tu práctica está activa", "Consulta el expediente para revisar el plan de trabajo, registrar avances u horas y seguir la actividad persistida.", "dossier", "Abrir expediente", state);
    case "DOCUMENTATION_PENDING": {
      if (activation?.ready_to_activate) {
        return journey("Los requisitos están listos para activación", "La consulta de requisitos indica que se cumplen las condiciones configuradas. La coordinación autorizada puede continuar con la activación.", "documents", "Consultar requisitos", state);
      }
      const studentDocumentAction = activation?.items.some((item) =>
        item.kind.startsWith("DOC_") && (item.status === "REQUIRED" || item.status === "REJECTED"),
      ) ?? false;
      if (studentDocumentAction) {
        return journey("Revisa tus documentos", "Hay documentos pendientes de entrega o corrección según los estados registrados. En Mis documentos puedes consultar cuáles requieren una entrega.", "documents", "Revisar documentos", state);
      }
      return journey("Consulta los requisitos de activación", "La práctica aún no está activa. Revisa en Mis documentos el estado de los requisitos registrados; algunos pueden estar en revisión o depender de otra relación autorizada.", "documents", "Consultar requisitos", state);
    }
    case "PENDING_ACADEMIC_APPROVAL":
      return journey("Tu selección está en revisión académica", "La coordinación del programa debe resolver la revisión registrada antes de que avance la etapa documental.", "applications", "Ver mi postulación", state);
    case "COMPLETED":
      return journey("La práctica está completada", "Consulta el expediente para revisar las evidencias y el historial. Las acciones posteriores solo aparecen para los roles autorizados.", "dossier", "Consultar expediente", state);
    case "CLOSED":
      return journey("La práctica está cerrada", "Consulta el expediente y la actividad histórica de la práctica.", "dossier", "Ver historial", state);
    case "REJECTED":
      return journey("La práctica fue rechazada", "Consulta en tus postulaciones el estado y la información disponible sobre la decisión.", "applications", "Ver mis postulaciones", state);
    case "CANCELLED":
      return journey("La práctica fue cancelada", "Consulta el expediente para revisar el estado y la actividad registrada.", "dossier", "Ver historial", state);
  }

  switch (application.state) {
    case "PENDING_ELIGIBILITY_REVIEW":
      return journey("Tu postulación requiere revisión académica", "La coordinación de tu programa debe resolver la elegibilidad antes de que la organización pueda revisar tu postulación.", "applications", "Ver estado de revisión", state);
    case "SUBMITTED":
      return journey("Tu postulación fue enviada", "El resultado de elegibilidad se registró y la postulación está pendiente de decisión por la organización anfitriona.", "applications", "Ver mi postulación", state);
    case "INELIGIBLE":
      return journey("La postulación no cumple la elegibilidad", "Consulta el resultado y los criterios visibles asociados a la versión de política usada al postularte.", "applications", "Consultar resultado", state);
    case "REJECTED":
      return journey("La postulación fue rechazada", "Consulta el historial para revisar el estado y la información disponible sobre la decisión.", "applications", "Ver mis postulaciones", state);
    case "SELECTED":
      return journey("Has sido seleccionado", "Consulta el estado de la postulación y la práctica relacionada.", application.placement_id ? "dossier" : "applications", application.placement_id ? "Consultar expediente" : "Ver mi postulación", state);
    default:
      return journey("Sigue el estado de tu postulación", "Consulta el historial para ver los datos persistidos y cualquier cambio registrado.", application.placement_id ? "dossier" : "applications", application.placement_id ? "Consultar expediente" : "Ver mis postulaciones", state);
  }
}
