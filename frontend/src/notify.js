// One place for user feedback: SweetAlert2 for confirmations, toastr for notifications.
import Swal from "sweetalert2";
import toastr from "toastr";
import "toastr/build/toastr.min.css";

toastr.options = {
  positionClass: "toast-bottom-right",
  closeButton: true,
  progressBar: true,
  newestOnTop: true,
  preventDuplicates: true,
  timeOut: 3500,
  extendedTimeOut: 1500,
};

export const notify = {
  success: (message, title) => toastr.success(message, title),
  error: (message, title) => toastr.error(message, title ?? "Error"),
  warning: (message, title) => toastr.warning(message, title),
  info: (message, title) => toastr.info(message, title),
};

/** Ask for a line of text (e.g. a new password). Resolves to the text, or null if cancelled. */
export async function promptDialog({ title, text = "", label = "", inputType = "text", confirmText = "OK" } = {}) {
  const result = await Swal.fire({
    title,
    text,
    input: inputType,
    inputLabel: label,
    inputAttributes: { autocomplete: "new-password" },
    showCancelButton: true,
    confirmButtonText: confirmText,
    reverseButtons: true,
    confirmButtonColor: cssVar("--accent") || "#2563eb",
    background: cssVar("--panel") || undefined,
    color: cssVar("--text") || undefined,
    inputValidator: (v) => (v ? undefined : "Please enter a value"),
  });
  return result.isConfirmed ? result.value : null;
}

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/** Ask the user to confirm an action. Resolves to true only if they confirm. */
export async function confirmDialog({
  title = "Are you sure?",
  text = "",
  confirmText = "Yes",
  cancelText = "Cancel",
  danger = false,
} = {}) {
  const result = await Swal.fire({
    title,
    text,
    icon: danger ? "warning" : "question",
    showCancelButton: true,
    confirmButtonText: confirmText,
    cancelButtonText: cancelText,
    confirmButtonColor: danger ? cssVar("--alert") || "#dc2626" : cssVar("--accent") || "#2563eb",
    focusCancel: danger, // make the safe choice the default for destructive actions
    reverseButtons: true,
    // follow the app's light/dark theme
    background: cssVar("--panel") || undefined,
    color: cssVar("--text") || undefined,
  });
  return result.isConfirmed;
}
