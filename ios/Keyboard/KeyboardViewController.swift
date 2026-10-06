import UIKit

final class KeyboardViewController: UIInputViewController {
    private let engine = MobileEngine()
    private let status = UILabel()
    private let candidates = UIStackView()
    private let keys = UIStackView()
    private var mode = UIButton(type: .system)
    private var language = UIButton(type: .system)
    private var palette = WordtrailPalette(theme: .current)
    private var heightConstraint: NSLayoutConstraint?
    private var state: MobileState?
    private var epoch = 0
    private var numbers = false
    private var upper = false
    private var capsLock = false
    private var lastShiftTap: TimeInterval = 0
    private var wide = false
    private var compact = false
    private var candidateHeight: NSLayoutConstraint?
    private let pronunciationPanel = UIStackView()
    private var layoutEnglish = false
    private var ownDocumentChange = false

    override func viewDidLoad() {
        super.viewDidLoad()
        buildInterface()
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        let nextWide = view.bounds.width >= 600
        let nextCompact = (view.window?.screen.bounds.height ?? 800) < 500
        if nextWide != wide || nextCompact != compact {
            wide = nextWide; compact = nextCompact; buildInterface()
        }
    }

    private func buildInterface() {
        palette = WordtrailPalette(theme: .current)
        overrideUserInterfaceStyle = palette.theme == .night ? .dark : .light
        for child in view.subviews { child.removeFromSuperview() }
        for item in candidates.arrangedSubviews { candidates.removeArrangedSubview(item); item.removeFromSuperview() }
        view.backgroundColor = palette.background
        mode = UIButton(type: .system); language = UIButton(type: .system)
        let root = UIStackView()
        root.axis = .vertical; root.spacing = 4
        root.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(root)
        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 6),
            root.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -6),
            root.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            root.widthAnchor.constraint(lessThanOrEqualToConstant: 1000),
            root.topAnchor.constraint(equalTo: view.topAnchor, constant: 9),
            root.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -8)
        ])
        let fill = root.widthAnchor.constraint(equalTo: view.widthAnchor, constant: -12); fill.priority = .defaultHigh; fill.isActive = true
        if heightConstraint == nil { let height = view.heightAnchor.constraint(equalToConstant: 300); height.priority = .defaultHigh; height.isActive = true; heightConstraint = height }
        let toolbar = UIStackView(); toolbar.spacing = 4; toolbar.alignment = .center
        toolbar.heightAnchor.constraint(equalToConstant: 32).isActive = true
        let brand = UILabel(); brand.text = "词伴"; brand.font = .systemFont(ofSize: 13, weight: .medium); brand.textColor = palette.accent
        brand.widthAnchor.constraint(equalToConstant: 36).isActive = true; toolbar.addArrangedSubview(brand)
        status.font = .systemFont(ofSize: 11);status.textColor = palette.muted;status.numberOfLines = 1;status.lineBreakMode = .byTruncatingTail
        status.setContentHuggingPriority(.defaultLow, for: .horizontal);status.setContentCompressionResistancePriority(.defaultLow, for: .horizontal);toolbar.addArrangedSubview(status)
        language.setTitle("EN 译词", for: .normal)
        language.addAction(UIAction { [weak self] _ in self?.cycleLanguage() }, for: .touchUpInside)
        language.titleLabel?.font = .systemFont(ofSize: 12); language.tintColor = palette.muted
        language.widthAnchor.constraint(equalToConstant: 82).isActive = true
        toolbar.addArrangedSubview(language)
        let themes = button("◐") {}
        themes.accessibilityLabel = "切换主题"
        let themeActions: [UIMenuElement] = WordtrailTheme.allCases.map { theme in
            UIAction(title: theme.title, state: palette.theme == theme ? .on : .off) { [weak self] _ in
                UserDefaults.standard.set(theme.rawValue, forKey: "theme"); self?.buildInterface()
            }
        }
        let selectedTargets = UserDefaults.standard.stringArray(forKey: "vocabularyTargets") ?? []
        let goals = [("cet4", "四级"), ("cet6", "六级"), ("tem4", "专四"), ("tem8", "专八"), ("toefl", "托福"), ("ielts", "雅思")]
        var targetActions: [UIMenuElement] = goals.map { id, label in
            UIAction(title: label, state: selectedTargets.contains(id) ? .on : .off) { [weak self] _ in
                var targets = UserDefaults.standard.stringArray(forKey: "vocabularyTargets") ?? []
                if targets.contains(id) { targets.removeAll { $0 == id } } else { targets.append(id) }
                UserDefaults.standard.set(targets, forKey: "vocabularyTargets")
                self?.send("vocabulary", ["vocabulary_targets": targets]); self?.buildInterface()
            }
        }
        targetActions.insert(UIAction(title: "全部词汇 / 清除目标", state: selectedTargets.isEmpty ? .on : .off) { [weak self] _ in
            UserDefaults.standard.set([String](), forKey: "vocabularyTargets")
            self?.send("vocabulary", ["vocabulary_targets": [String]()]); self?.buildInterface()
        }, at: 0)
        themes.menu = UIMenu(title: "主题与学习目标", children: themeActions + [UIMenu(title: "英语学习目标（可多选）", children: targetActions)])
        themes.showsMenuAsPrimaryAction = true
        for item in [themes, button("‹") { [weak self] in self?.send("previous_page") }, button("›") { [weak self] in self?.send("next_page") }] {
            item.widthAnchor.constraint(equalToConstant: 28).isActive = true; item.backgroundColor = palette.background; item.setTitleColor(palette.muted, for: .normal); toolbar.addArrangedSubview(item)
        }
        root.addArrangedSubview(toolbar)
        status.text = "正在准备词库…"
        let scroll = UIScrollView(); scroll.showsHorizontalScrollIndicator = false
        candidateHeight = scroll.heightAnchor.constraint(equalToConstant: 72); candidateHeight?.isActive = true
        candidates.axis = .horizontal; candidates.spacing = 4
        candidates.translatesAutoresizingMaskIntoConstraints = false
        scroll.addSubview(candidates)
        NSLayoutConstraint.activate([
            candidates.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor),
            candidates.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor),
            candidates.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor),
            candidates.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor),
            candidates.heightAnchor.constraint(equalTo: scroll.frameLayoutGuide.heightAnchor)
        ])
        root.addArrangedSubview(scroll)
        for item in pronunciationPanel.arrangedSubviews { pronunciationPanel.removeArrangedSubview(item); item.removeFromSuperview() }
        pronunciationPanel.axis = .vertical; pronunciationPanel.isHidden = true; root.addArrangedSubview(pronunciationPanel)
        keys.axis = .vertical; keys.spacing = 4; root.addArrangedSubview(keys)
        buildKeys()
        if let state { render(state, applyDocumentChange: false) } else { send("state") }
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        epoch += 1; send("reset")
    }
    override func viewWillDisappear(_ animated: Bool) {
        epoch += 1; send("reset"); send("flush")
        super.viewWillDisappear(animated)
    }
    override func textDidChange(_ textInput: UITextInput?) {
        super.textDidChange(textInput)
        if !ownDocumentChange, let state, !state.input.isEmpty() {
            epoch += 1; send("reset")
        }
    }

    private func send(_ operation: String, _ fields: [String: Any] = [:]) {
        let generation = epoch
        var request = fields; request["op"] = operation
        engine.perform(request) { [weak self] result in
            guard let self, generation == self.epoch else { return }
            switch result {
            case .success(let value):
                if operation != "flush" { self.render(value) }
            case .failure:
                self.status.alpha = 1;self.status.text = "暂时无法生成候选，请切换键盘后重试"
            }
        }
    }

    private func render(_ value: MobileState, applyDocumentChange: Bool = true) {
        state = value
        ownDocumentChange = true
        if applyDocumentChange {
            if let commit = value.commit { textDocumentProxy.insertText(commit) }
            if value.deleteBackward { textDocumentProxy.deleteBackward() }
        }
        ownDocumentChange = false
        if layoutEnglish != value.english { buildKeys() }
        updateMode()
        language.setTitle(value.language.uppercased() + " 译词", for: .normal)
        status.text = value.preedit.isEmpty ? "点选中文 · 长按输入译词" : "\(value.preedit)  \(value.page + 1)/\(max(value.pageCount, 1))"
        status.alpha = value.preedit.isEmpty ? 0 : 1
        pronunciationPanel.isHidden = true
        for view in candidates.arrangedSubviews { candidates.removeArrangedSubview(view); view.removeFromSuperview() }
        if value.candidates.isEmpty {
            let tip = UILabel(); tip.text = value.english ? "英文输入 · 点中/英切回拼音" : "点选中文 · 长按输入译词"; tip.font = .systemFont(ofSize: 11); tip.textColor = palette.muted
            candidates.addArrangedSubview(tip)
        }
        for (index, candidate) in value.candidates.enumerated() {
            let item = UIButton(type: .system)
            item.titleLabel?.numberOfLines = 2
            item.backgroundColor = index == 0 ? palette.soft : palette.background; item.layer.cornerRadius = 12
            item.contentEdgeInsets = UIEdgeInsets(top: 3, left: 10, bottom: 19, right: 10)
            let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .center; paragraph.lineBreakMode = .byTruncatingTail
            let title = NSMutableAttributedString(string: candidate.text + "\n", attributes: [.font: UIFont.systemFont(ofSize: 20, weight: .medium), .foregroundColor: index == 0 ? palette.accent : palette.ink])
            let tags = candidate.translationSenses?.first?.tags ?? []
            let tagSummary = tags.isEmpty ? "" : " [" + tags.prefix(2).map { $0.label }.joined(separator: "/") + (tags.count > 2 ? "+\(tags.count - 2)" : "") + "]"
            title.append(NSAttributedString(string: candidate.annotation + tagSummary, attributes: [.font: UIFont.systemFont(ofSize: 10), .foregroundColor: candidate.fresh ? palette.fresh : palette.muted]))
            title.addAttribute(.paragraphStyle, value: paragraph, range: NSRange(location: 0, length: title.length))
            item.setAttributedTitle(title, for: .normal)
            item.widthAnchor.constraint(equalToConstant: wide ? 142 : 118).isActive = true
            item.titleLabel?.lineBreakMode = .byTruncatingTail
            item.accessibilityLabel = candidate.text + " " + candidate.annotation
            item.addAction(UIAction { [weak self] _ in self?.send("select", ["index": candidate.id, "revision": value.revision]) }, for: .touchUpInside)
            item.tag = candidate.id
            let detail = UIButton(type: .system); detail.setTitle(candidate.pronunciation == nil ? "释义 ▾" : "音标 ▾", for: .normal)
            detail.titleLabel?.font = .systemFont(ofSize: 10); detail.setTitleColor(palette.muted, for: .normal); detail.translatesAutoresizingMaskIntoConstraints = false
            detail.accessibilityLabel = "查看\(candidate.text)的音标和释义"
            detail.addAction(UIAction { [weak self] _ in self?.showPronunciation(candidate) }, for: .touchUpInside)
            item.addSubview(detail)
            NSLayoutConstraint.activate([detail.leadingAnchor.constraint(equalTo: item.leadingAnchor), detail.trailingAnchor.constraint(equalTo: item.trailingAnchor), detail.bottomAnchor.constraint(equalTo: item.bottomAnchor, constant: -2), detail.heightAnchor.constraint(equalToConstant: 18)])
            let swipe = UISwipeGestureRecognizer(target: self, action: #selector(expandCandidate(_:))); swipe.direction = .down; item.addGestureRecognizer(swipe)
            let gesture = UILongPressGestureRecognizer(target: self, action: #selector(translateCandidate(_:)))
            item.addGestureRecognizer(gesture)
            candidates.addArrangedSubview(item)
        }
        updateHeight()
    }

    private func updateHeight() {
        let rowHeight: CGFloat = compact ? 38 : wide ? 52 : 46
        let gaps: CGFloat = pronunciationPanel.isHidden ? 2 : 3
        heightConstraint?.constant = 32 + 72 + rowHeight * 4 + 12 + 17 + gaps * 4 + view.safeAreaInsets.bottom + (pronunciationPanel.isHidden ? 0 : 108)
    }
    @objc private func expandCandidate(_ gesture: UISwipeGestureRecognizer) {
        guard let id = gesture.view?.tag, let candidate = state?.candidates.first(where: { $0.id == id }) else { return }
        showPronunciation(candidate)
    }
    private func showPronunciation(_ candidate: MobileCandidate) {
        for item in pronunciationPanel.arrangedSubviews { pronunciationPanel.removeArrangedSubview(item); item.removeFromSuperview() }
        pronunciationPanel.backgroundColor = palette.surface; pronunciationPanel.layer.cornerRadius = 12
        let header = UIStackView(); header.alignment = .center; header.layoutMargins = UIEdgeInsets(top: 0, left: 12, bottom: 0, right: 6); header.isLayoutMarginsRelativeArrangement = true
        let title = UILabel(); title.text = (candidate.pronunciation?.word ?? candidate.text) + " · " + (candidate.pronunciation == nil ? "释义" : "音标"); title.font = .systemFont(ofSize: 12, weight: .medium); title.textColor = palette.accent
        header.addArrangedSubview(title)
        let close = button("收起") { [weak self] in self?.pronunciationPanel.isHidden = true; self?.updateHeight() }; close.titleLabel?.font = .systemFont(ofSize: 12); close.backgroundColor = palette.surface; close.widthAnchor.constraint(equalToConstant: 54).isActive = true
        header.addArrangedSubview(close); header.heightAnchor.constraint(equalToConstant: 28).isActive = true; pronunciationPanel.addArrangedSubview(header)
        let scroll = UIScrollView(); scroll.heightAnchor.constraint(equalToConstant: 80).isActive = true
        let label = UILabel(); label.numberOfLines = 0; label.font = .systemFont(ofSize: 13); label.textColor = palette.ink
        var text = candidate.annotation
        if let senses = candidate.translationSenses {
            for sense in senses {
                text += "\n" + sense.text + " · " + (sense.tags.isEmpty ? "暂无考试标签" : sense.tags.map { $0.label }.joined(separator: " / "))
                let sources = Array(Set(sense.tags.flatMap { $0.sources })).sorted()
                if !sources.isEmpty { text += "\n词表来源：" + sources.joined(separator: " / ") }
                if let ipa = sense.pronunciation { if let uk = ipa.uk { text += "\n英式  " + uk }; if let us = ipa.us { text += "\n美式  " + us } }
            }
        } else if let ipa = candidate.pronunciation { if let uk = ipa.uk { text += "\n英式  " + uk }; if let us = ipa.us { text += "\n美式  " + us } }
        label.text = text; label.translatesAutoresizingMaskIntoConstraints = false; scroll.addSubview(label)
        NSLayoutConstraint.activate([label.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor, constant: 12), label.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor, constant: -12), label.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor, constant: 3), label.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor, constant: -10), label.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor, constant: -24)])
        pronunciationPanel.addArrangedSubview(scroll); pronunciationPanel.isHidden = false; updateHeight()
    }

    @objc private func translateCandidate(_ gesture: UILongPressGestureRecognizer) {
        guard gesture.state == .began, let item = gesture.view, let state,
              state.candidates.contains(where: { $0.id == item.tag && !$0.annotation.isEmpty }) else { return }
        send("translation", ["index": item.tag, "revision": state.revision])
    }
    private func cycleLanguage() {
        let current = state?.language ?? "en"
        let next = current == "en" ? "ja" : current == "ja" ? "es" : "en"
        UserDefaults.standard.set(next, forKey: "learningLanguage")
        send("language", ["language": next])
    }
    private func buildKeys() {
        layoutEnglish = state?.english == true
        for view in keys.arrangedSubviews { keys.removeArrangedSubview(view); view.removeFromSuperview() }
        let rows = numbers ? ["1234567890", "-/:;()&@\"", ".,?!'"] : ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
        for (index, letters) in rows.enumerated() {
            let row = UIStackView(); row.spacing = 3; row.distribution = .fillEqually
            row.heightAnchor.constraint(equalToConstant: compact ? 38 : wide ? 52 : 46).isActive = true
            if index == 1 && !numbers { row.isLayoutMarginsRelativeArrangement = true; row.layoutMargins = UIEdgeInsets(top: 0, left: wide ? 46 : 16, bottom: 0, right: wide ? 46 : 16) }
            if index == 2 {
                let shift = symbolButton(capsLock ? "capslock.fill" : upper ? "shift.fill" : "shift", description: capsLock ? "大写锁定" : "大写") { [weak self] in self?.shift() }
                if upper { shift.backgroundColor = palette.accent; shift.tintColor = palette.onAccent }; row.addArrangedSubview(shift)
            }
            for letter in letters {
                let value = String(letter)
                row.addArrangedSubview(button(numbers ? value : self.layoutEnglish && !self.upper ? value : value.uppercased()) { [weak self] in
                    guard let self else { return }
                    self.send("key", ["text": self.upper && self.state?.english == true ? value.uppercased() : value])
                    if self.upper && !self.capsLock { self.upper = false; self.buildKeys() }
                })
            }
            if index == 2 { row.addArrangedSubview(symbolButton("delete.left", description: "删除") { [weak self] in self?.send("backspace") }) }
            keys.addArrangedSubview(row)
        }
        let bottom = UIStackView(); bottom.spacing = 4; bottom.distribution = .fill
        bottom.heightAnchor.constraint(equalToConstant: compact ? 38 : wide ? 52 : 46).isActive = true
        let symbols = button(numbers ? "ABC" : "123") { [weak self] in self?.numbers.toggle(); self?.buildKeys() }; symbols.titleLabel?.font = .systemFont(ofSize: 14)
        mode = button("中/英") { [weak self] in self?.upper = false; self?.capsLock = false; self?.send("toggle") }; mode.titleLabel?.font = .systemFont(ofSize: 12)
        let globe = symbolButton("globe", description: "切换键盘") {}
        globe.addTarget(self, action: #selector(handleInputModeList(from:with:)), for: .allTouchEvents)
        let comma = button(layoutEnglish ? "," : "，") { [weak self] in self?.send("key", ["text": ","]) }
        let space = button("空格") { [weak self] in self?.send("space") }
        let period = button(layoutEnglish ? "." : "。") { [weak self] in self?.send("key", ["text": "."]) }
        let enter = symbolButton("return", description: "回车") { [weak self] in self?.send("enter") }; enter.backgroundColor = palette.accent; enter.tintColor = palette.onAccent
        let items: [(UIButton, CGFloat)] = [(symbols,1.25),(mode,1.4),(globe,1),(comma,0.7),(space,3.5),(period,0.7),(enter,1.3)]
        for (item, weight) in items {
            item.setContentHuggingPriority(.defaultLow, for: .horizontal); item.setContentCompressionResistancePriority(.defaultLow, for: .horizontal); bottom.addArrangedSubview(item)
            if item !== space { item.widthAnchor.constraint(equalTo: space.widthAnchor, multiplier: weight / 3.5).isActive = true }
        }
        keys.addArrangedSubview(bottom)
        updateMode()
    }
    private func updateMode() {
        let english = state?.english == true
        let label = NSMutableAttributedString(string: "中/英", attributes: [.font: UIFont.systemFont(ofSize: 12, weight: .medium), .foregroundColor: palette.muted])
        label.addAttribute(.foregroundColor, value: palette.accent, range: NSRange(location: english ? 2 : 0, length: 1)); mode.setAttributedTitle(label, for: .normal)
        mode.accessibilityLabel = "切换中英文，当前" + (english ? "英文" : "中文")
    }
    private func shift() {
        let now = ProcessInfo.processInfo.systemUptime
        if upper && now - lastShiftTap < 0.35 { capsLock = true } else { upper.toggle(); capsLock = false }
        lastShiftTap = now
        if upper && state?.english != true { send("toggle") }
        buildKeys()
    }
    private func symbolButton(_ symbol: String, description: String, action: @escaping () -> Void) -> UIButton {
        let item = button("", action: action); item.setImage(UIImage(systemName: symbol, withConfiguration: UIImage.SymbolConfiguration(pointSize: 20, weight: .regular)), for: .normal)
        item.tintColor = palette.ink; item.contentHorizontalAlignment = .center; item.contentVerticalAlignment = .center; item.accessibilityLabel = description
        return item
    }
    private func button(_ title: String, action: @escaping () -> Void) -> UIButton {
        let item = UIButton(type: .system)
        item.setTitle(title, for: .normal)
        let letter = title.range(of: "^[a-zA-Z0-9]$", options: .regularExpression) != nil
        item.titleLabel?.font = .systemFont(ofSize: letter ? 21 : 16)
        item.setTitleColor(palette.ink, for: .normal)
        item.backgroundColor = letter ? palette.key : palette.function
        item.layer.cornerRadius = 10
        if title.trimmingCharacters(in: .whitespaces) == "空格" { item.backgroundColor = palette.key; item.setTitleColor(palette.muted, for: .normal); item.titleLabel?.font = .systemFont(ofSize: 14) }
        if title == "↵" || (title == "⇧" && upper) { item.backgroundColor = palette.accent; item.setTitleColor(palette.onAccent, for: .normal) }
        item.addAction(UIAction { _ in action() }, for: .touchUpInside)
        return item
    }
}
