import { Button, Modal } from "@gravity-ui/uikit";
import PropTypes from "prop-types";

export function Page({ children, style = null }) {
  return (
    <main
      style={{
        width: "min(1120px, calc(100% - 32px))",
        margin: "0 auto",
        display: "grid",
        gap: 16,
        ...style,
      }}
    >
      {children}
    </main>
  );
}

Page.propTypes = {
  children: PropTypes.node.isRequired,
  style: PropTypes.object,
};

export function SectionCard({ children, style = null, ...sectionProps }) {
  return (
    <section
      {...sectionProps}
      style={{
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 8,
        padding: 16,
        display: "grid",
        gap: 12,
        ...style,
      }}
    >
      {children}
    </section>
  );
}

SectionCard.propTypes = {
  children: PropTypes.node.isRequired,
  style: PropTypes.object,
};

export function DangerCard({ children, style = null }) {
  return (
    <SectionCard
      style={{
        borderColor: "rgba(255, 77, 79, 0.42)",
        background: "rgba(255, 77, 79, 0.06)",
        ...style,
      }}
    >
      {children}
    </SectionCard>
  );
}

DangerCard.propTypes = SectionCard.propTypes;

export function FormActions({ children, style = null }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "flex-end",
        gap: 8,
        flexWrap: "wrap",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

FormActions.propTypes = {
  children: PropTypes.node.isRequired,
  style: PropTypes.object,
};

export function InlineNotice({ children, tone = "info", style = null }) {
  const palette =
    tone === "danger"
      ? ["rgba(255,77,79,0.16)", "rgba(255,77,79,0.42)"]
      : ["rgba(82,130,255,0.14)", "rgba(82,130,255,0.36)"];
  return (
    <div
      role="status"
      style={{
        border: `1px solid ${palette[1]}`,
        background: palette[0],
        borderRadius: 8,
        padding: "10px 12px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

InlineNotice.propTypes = {
  children: PropTypes.node.isRequired,
  tone: PropTypes.oneOf(["info", "danger"]),
  style: PropTypes.object,
};

export function SkeletonCard({ children, minHeight = 160 }) {
  return (
    <SectionCard
      style={{ minHeight }}
      aria-hidden="true"
      className="skeleton-block"
    >
      {children}
    </SectionCard>
  );
}

SkeletonCard.propTypes = {
  children: PropTypes.node.isRequired,
  minHeight: PropTypes.number,
};

export function ConfirmDialog({
  open,
  title,
  children,
  confirmText = "Подтвердить",
  cancelText = "Отмена",
  onConfirm,
  onCancel,
  loading = false,
}) {
  return (
    <Modal open={open} onClose={onCancel}>
      <div style={{ padding: 20, display: "grid", gap: 16, maxWidth: 420 }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        <div>{children}</div>
        <FormActions>
          <Button view="flat" onClick={onCancel} disabled={loading}>
            {cancelText}
          </Button>
          <Button view="action" onClick={onConfirm} loading={loading}>
            {confirmText}
          </Button>
        </FormActions>
      </div>
    </Modal>
  );
}

ConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  loading: PropTypes.bool,
};
