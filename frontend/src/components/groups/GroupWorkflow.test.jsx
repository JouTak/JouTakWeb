import { ThemeProvider, Toaster, ToasterProvider } from "@gravity-ui/uikit";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GroupManage from "../../pages/groups/GroupManage";
import * as api from "../../services/api/groupsApi";
import { MyGroups } from "./AccountGroups";
import GroupEditor from "./GroupEditor";
import GroupMemberDialog from "./GroupMemberDialog";
import GroupParticipation from "./GroupParticipation";
import GroupProcessActions from "./GroupProcessActions";

vi.mock("../../services/api/groupsApi", () => ({
  getGroup: vi.fn(),
  getGroupHistory: vi.fn(),
  getGroupMembers: vi.fn(),
  getGroupProcesses: vi.fn(),
  getMyGroups: vi.fn(),
  saveGroup: vi.fn(),
  joinGroup: vi.fn(),
  applyToGroup: vi.fn(),
  leaveGroup: vi.fn(),
  setGroupVisibility: vi.fn(),
  respondGroupInvitation: vi.fn(),
  respondGroupLeadership: vi.fn(),
  withdrawMyGroupRequest: vi.fn(),
  offerGroupLeadership: vi.fn(),
  removeGroupMember: vi.fn(),
  restrictGroupMember: vi.fn(),
  changeGroupRole: vi.fn(),
  uploadGroupImage: vi.fn(),
}));
const group = {
  slug: "builders",
  name: "Мастерская",
  short_description: "Строим вместе",
  description: "Первый текст",
  rules: "Уважение",
  welcome: "",
  application_question: "Ваш проект?",
  contacts: [],
  category: "club",
  status: "active",
  access: "public",
  join_mode: "open",
  accepting: true,
  version: 1,
  viewer: { state: "eligible", membership: null },
  capabilities: { write_enabled: true, join: true },
};
function show(node, search = "") {
  return render(
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={new Toaster()}>
        <RouterProvider
          router={createMemoryRouter(
            [{ path: "/groups/:slug/manage", element: node }],
            { initialEntries: [`/groups/builders/manage${search}`] },
          )}
        />
      </ToasterProvider>
    </ThemeProvider>,
  );
}
describe("Player group workflows", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);
  it("keeps past participation without linking to an inaccessible group", async () => {
    api.getMyGroups.mockResolvedValue({
      items: [{ group: null, membership: { id: 7, status: "left" } }],
      page: 1,
      total: 1,
    });
    show(<MyGroups history />);
    await screen.findByRole("heading", { name: "Объединение недоступно" });
    expect(screen.getByText(/История вашего участия сохранена/)).toBeVisible();
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/communities");
  });
  it("requires explicit consent and keeps participation private by default", async () => {
    api.joinGroup.mockResolvedValue(group);
    show(<GroupParticipation group={group} />);
    expect(api.joinGroup).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Вступить", exact: true }),
    );
    await waitFor(() =>
      expect(api.joinGroup).toHaveBeenCalledWith("builders", {
        visibility: "private",
      }),
    );
  });
  it("preserves a failed request answer and presents the server explanation", async () => {
    api.applyToGroup.mockRejectedValue({
      response: { data: { detail: "Набор приостановлен" } },
    });
    show(
      <GroupParticipation
        group={{
          ...group,
          join_mode: "approval",
          capabilities: { write_enabled: true, apply: true },
        }}
      />,
    );
    fireEvent.change(screen.getByLabelText("Ваш проект?"), {
      target: { value: "Мост" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Отправить заявку" }));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("Ваш проект?")).toHaveValue("Мост");
    expect(screen.getByRole("alert")).toHaveTextContent("Набор приостановлен");
  });
  it("allows declining on pause but prevents accepting", async () => {
    api.respondGroupInvitation.mockResolvedValue({ status: "declined" });
    show(
      <GroupProcessActions
        process={{ id: 12, kind: "invitation", status: "pending" }}
        group={{ ...group, accepting: false }}
        writeEnabled
      />,
    );
    expect(
      screen.getByRole("button", { name: "Принять приглашение" }),
    ).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Отказаться" }));
    await waitFor(() =>
      expect(api.respondGroupInvitation).toHaveBeenCalledWith(12, {
        decision: "decline",
        visibility: "private",
      }),
    );
  });
  it("loads history only after opening the section", async () => {
    api.getGroup.mockResolvedValue({
      ...group,
      viewer: { state: "member", membership: { role: "manager" } },
      capabilities: {
        manage: true,
        configure: true,
        edit: true,
        write_enabled: true,
      },
    });
    api.getGroupHistory.mockResolvedValue({ items: [], total: 0, page: 1 });
    show(<GroupManage />);
    await screen.findByRole("heading", { name: "Основное" });
    expect(api.getGroupHistory).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "История", exact: true }),
    );
    await waitFor(() =>
      expect(api.getGroupHistory).toHaveBeenCalledWith("builders", 1),
    );
  });
  it("keeps the content draft on a version conflict", async () => {
    api.saveGroup.mockRejectedValue({
      response: { data: { detail: "Данные изменились" } },
    });
    show(
      <GroupEditor group={{ ...group, capabilities: { edit: true } }} />,
      "?section=description",
    );
    fireEvent.change(screen.getByLabelText("Чем занимаемся"), {
      target: { value: "Мой несохранённый текст" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Сохранить", exact: true }),
    );
    await screen.findByRole("alert");
    expect(screen.getByLabelText("Чем занимаемся")).toHaveValue(
      "Мой несохранённый текст",
    );
  });
  it("does not send a transfer before confirming its consequence", async () => {
    api.offerGroupLeadership.mockResolvedValue({ status: "pending" });
    show(
      <GroupMemberDialog
        group={group}
        member={{ id: 5, username: "builder", role: "member" }}
        operation="transfer"
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/а вы — обычным участником/)).toBeVisible();
    expect(api.offerGroupLeadership).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Передать руководство", exact: true }),
    );
    await waitFor(() =>
      expect(api.offerGroupLeadership).toHaveBeenCalledWith("builders", {
        membership_id: 5,
        transfer: true,
      }),
    );
  });
});
