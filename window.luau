--!strict

local ui = tern.ui
local TITLE = "CC Switch 额度"
local POLL_MS = 5 * 60 * 1000
local MAX_STATUS_CARDS = 3
local cards: { any } = {}
local last_error: string? = nil
local loading = false

local function number(value: any): number?
	if type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge then
		return value
	end
	return nil
end

local function percent(row: any): number?
	local total = number(row.total)
	local left = number(row.remaining)
	if total and total > 0 and left then
		return math.clamp(left / total * 100, 0, 100)
	end
	if row.unit == "%" and left then
		return math.clamp(left, 0, 100)
	end
	return nil
end

local function short_value(row: any): string
	local left = number(row.remaining)
	if not left then
		return "—"
	end
	local unit = if type(row.unit) == "string" then row.unit else ""
	if unit == "%" then
		return string.format("%.0f%%", left)
	end
	if unit == "USD" or unit == "$" then
		return string.format("$%.2f", left)
	end
	return string.format("%.1f%s", left, if unit == "" then "" else " " .. unit)
end

local function tone(row: any, for_view: boolean): string
	local value = percent(row)
	if value == nil then
		return "muted"
	elseif value <= 5 then
		return "error"
	elseif value <= 20 then
		return if for_view then "warning" else "warn"
	end
	return "accent"
end

local function primary(card: any): any
	local selected: any = nil
	local lowest: number? = nil
	for _, row in card.data do
		if type(row) == "table" and row.isValid ~= false then
			local value = percent(row)
			if selected == nil or (value ~= nil and (lowest == nil or value < lowest)) then
				selected = row
				lowest = value
			end
		end
	end
	return selected
end

local function status_segments(_pane: PaneInfo): { StatusSegment }
	local action = "plugin.cc-switch-quotas.open"
	if #cards == 0 then
		return { {
			text = if last_error then "CC Switch 读取失败" elseif loading then "CC Switch 读取中…" else "CC Switch · 无额度",
			tone = if last_error then "error" else "muted",
			command = action,
		} }
	end
	local segments: { StatusSegment } = {}
	if last_error then
		table.insert(segments, { text = "CC Switch 数据未更新", tone = "error", command = action })
	end
	for index, card in cards do
		if index > MAX_STATUS_CARDS then
			break
		end
		local row = primary(card)
		table.insert(segments, {
			text = card.app .. " · " .. card.name .. " " .. (if row then short_value(row) else "—"),
			tone = if row then tone(row, false) else "muted",
			command = action,
		})
	end
	if #cards > MAX_STATUS_CARDS then
		table.insert(segments, { text = "+" .. tostring(#cards - MAX_STATUS_CARDS), command = action })
	end
	return segments
end

local function quota_view(): Node
	local children: { Node } = {
		ui.row({
			ui.text(TITLE),
			ui.node("badge", {
				key = "refresh",
				text = if loading then "刷新中…" else "刷新",
				tone = "accent",
				actions = { click = "refresh" },
			}),
		}),
	}
	if last_error then
		table.insert(children, ui.badge(last_error, "error"))
	end
	if #cards == 0 then
		table.insert(children, ui.text(if loading then "正在查询额度…" else "没有找到已启用额度查询的当前供应商。"))
	end
	for index, card in cards do
		local details: { Node } = {}
		if type(card.error) == "string" then
			table.insert(details, ui.badge(card.error, "error"))
		end
		for _, row in card.data do
			if type(row) == "table" then
				local label = if type(row.planName) == "string" and row.planName ~= "" then row.planName else "额度"
				table.insert(details, ui.row({ ui.text(label), ui.badge("剩余 " .. short_value(row), tone(row, true)) }))
				local value = percent(row)
				if value then
					table.insert(details, ui.progress(1 - value / 100))
				end
				if type(row.extra) == "string" and row.extra ~= "" then
					table.insert(details, ui.text(row.extra))
				end
				if type(row.invalidMessage) == "string" and row.invalidMessage ~= "" then
					table.insert(details, ui.badge(row.invalidMessage, "warning"))
				end
			end
		end
		local panel = ui.card({ ui.span(card.app .. " · " .. card.name, "strong") }, details)
		panel.p = panel.p or {}
		panel.p.key = "card-" .. tostring(index)
		table.insert(children, panel)
	end
	return ui.col(children)
end

local function update_canvases(cx: WindowCx)
	local view = quota_view()
	for _, canvas in cx.canvas:list() do
		if canvas.owner == tern.plugin.id and canvas.title == TITLE then
			cx.canvas:set(canvas.pane, { view = view })
		end
	end
end

local function read_quotas()
	if loading then
		return
	end
	loading = true
	tern.chrome.refresh()
	local home = tern.getenv("HOME") or ""
	local config = tern.getenv("CC_SWITCH_CONFIG_DIR")
	local config_dir = if config and config ~= "" then config else home .. "/.cc-switch"
	tern.process.run({ "python3", tern.plugin.dir .. "/quota_helper.py", config_dir }, { timeout_ms = 150000 }, function(result, cx)
		loading = false
		if result.status ~= 0 or result.timed_out then
			last_error = if result.timed_out then "CC Switch 额度查询超时" else "无法运行额度查询辅助程序（需 Python 3 和 Node.js）"
		else
			local ok, decoded = pcall(tern.json.decode, result.stdout)
			if ok and type(decoded) == "table" and type(decoded.cards) == "table" then
				if type(decoded.error) == "string" then
					last_error = decoded.error
				else
					cards = decoded.cards
					last_error = nil
				end
			else
				last_error = "CC Switch 额度数据格式不正确"
			end
		end
		tern.chrome.refresh()
		if cx then
			update_canvases(cx)
		end
	end)
end

local function poll()
	read_quotas()
	tern.timer(POLL_MS, poll)
end

tern.chrome.status(status_segments)

tern.command({
	id = "open",
	title = "打开 CC Switch 额度",
	icon = "meter",
	run = function(cx)
		for _, canvas in cx.canvas:list() do
			if canvas.owner == tern.plugin.id and canvas.title == TITLE then
				cx.canvas:set(canvas.pane, { view = quota_view() })
				cx.layout:focus(canvas.pane)
				return
			end
		end
		local pane, err = cx.canvas:open({
			title = TITLE,
			about = "显示 CC Switch 当前供应商已启用的额度查询结果。",
			view = quota_view(),
			how = "beside",
		})
		if not pane then
			cx:toast("error", "无法打开 CC Switch 额度", err)
		end
	end,
})

tern.on("canvas_action", function(event, cx)
	if event.owner ~= tern.plugin.id or event.act ~= "refresh" then
		return false
	end
	read_quotas()
	update_canvases(cx)
	return true
end)

poll()
