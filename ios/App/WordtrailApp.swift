import SwiftUI
import UIKit

@main
struct WordtrailApp: App {
    @State private var testInput = ""
    @State private var showNotices = false
    @AppStorage("theme") private var themeName = "jade"
    private var theme: WordtrailTheme { WordtrailTheme(rawValue: themeName) ?? .jade }
    private var palette: WordtrailPalette { WordtrailPalette(theme: theme) }
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack(spacing: 12) {
                            Image("WordtrailMark").resizable().scaledToFit()
                                .frame(width: 48, height: 48).clipShape(RoundedRectangle(cornerRadius: 16))
                                .accessibilityLabel("词伴小书灵图标")
                            VStack(alignment: .leading, spacing: 3) {
                                Text("词伴输入法").font(.system(size: 23, weight: .semibold))
                                Text("WORDTRAIL").font(.system(size: 10, weight: .medium)).tracking(2).foregroundStyle(Color(palette.muted))
                            }
                            Spacer()
                            Text("本地运行").font(.system(size: 11, weight: .medium)).foregroundStyle(Color(palette.accent))
                                .padding(.horizontal, 10).padding(.vertical, 7).background(Color(palette.soft), in: Capsule())
                        }
                        Text("好好打字，\n顺便认识一个新单词。").font(.system(size: 26, weight: .semibold)).lineSpacing(3).padding(.top, 8)
                        Text("中文是主角，译词轻轻陪伴。").font(.system(size: 13)).foregroundStyle(Color(palette.muted))
                        card {
                            HStack { Text("试打一下").font(.system(size: 15, weight: .semibold)); Spacer(); Text("nihao → 你好 / hello").font(.system(size: 11)).foregroundStyle(Color(palette.muted)) }
                            TextField("切换到词伴，在这里输入拼音…", text: $testInput, axis: .vertical)
                                .font(.system(size: 19)).lineLimit(2...3).padding(12).background(Color(palette.background), in: RoundedRectangle(cornerRadius: 12))
                        }
                        card {
                            Text("让词伴陪你打字").font(.system(size: 16, weight: .semibold))
                            Text("设置 → 通用 → 键盘 → 添加新键盘，选择词伴。再在输入框中长按地球键切换。").font(.system(size: 13)).foregroundStyle(Color(palette.muted)).lineSpacing(4)
                            Button("打开系统设置") { if let url=URL(string:UIApplication.openSettingsURLString){UIApplication.shared.open(url)} }
                                .font(.system(size: 15, weight: .medium)).frame(maxWidth: .infinity).padding(.vertical, 13)
                                .foregroundStyle(Color(palette.onAccent)).background(Color(palette.accent), in: RoundedRectangle(cornerRadius: 13))
                        }
                        card {
                            Text("换一种心情").font(.system(size: 16, weight: .semibold))
                            HStack(spacing: 8) {
                                ForEach(WordtrailTheme.allCases) { option in
                                    Button { themeName=option.rawValue } label: {
                                        Text(option.title).font(.system(size: 13, weight: .medium)).frame(maxWidth: .infinity).padding(.vertical, 12)
                                            .foregroundStyle(Color(theme==option ? palette.accent : palette.muted))
                                            .background(Color(theme==option ? palette.soft : palette.surface), in: RoundedRectangle(cornerRadius: 11))
                                    }
                                }
                            }
                            Text("这里预览应用外观；键盘主题请点键盘上的 ◐ 选择。").font(.system(size: 12)).foregroundStyle(Color(palette.muted))
                        }
                        Text("点选输入中文 · 长按输入译词\n键盘上点 EN 译词，切换英语、日语和西班牙语。\n无需“允许完全访问”，词库与熟悉度留在手机里。")
                            .font(.system(size: 12)).foregroundStyle(Color(palette.muted)).lineSpacing(5)
                        Button("开源许可与数据来源") { showNotices=true }.font(.system(size: 12)).foregroundStyle(Color(palette.accent))
                        Text("独立移动实验版 0.1.19 · 基于青简开源内核").font(.system(size: 10)).foregroundStyle(Color(palette.muted))
                    }.padding(20).foregroundStyle(Color(palette.ink))
                }.background(Color(palette.background)).toolbar(.hidden, for: .navigationBar)
                .sheet(isPresented: $showNotices) {
                    ScrollView { Text((Bundle.main.url(forResource: "NOTICE", withExtension: "txt").flatMap { try? String(contentsOf: $0, encoding: .utf8) }) ?? "许可文件不可用").font(.footnote).textSelection(.enabled).padding() }
                }
            }.preferredColorScheme(theme == .night ? .dark : .light).tint(Color(palette.accent))
        }
    }
    private func card<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12, content: content).frame(maxWidth: .infinity, alignment: .leading).padding(16)
            .background(Color(palette.surface), in: RoundedRectangle(cornerRadius: 20))
            .overlay(RoundedRectangle(cornerRadius: 20).stroke(Color(palette.line), lineWidth: 1))
    }
}
