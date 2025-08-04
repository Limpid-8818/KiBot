import asyncio
import os

from playwright.async_api import async_playwright

from infra.logger import logger


class BilibiliScreenshot:
    """B站动态截图工具"""
    
    def __init__(self):
        self.cache_dir = "cache/bilibili_screenshots"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def fetch_dynamic_screenshot(self, dynamic_id: str, mode: str = "mobile") -> str:
        """
        使用 Playwright 异步模式截图指定动态，默认用移动端截图，
        """
        url = f"https://t.bilibili.com/{dynamic_id}"
        output_filename = os.path.join(self.cache_dir, f"{dynamic_id}.png")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--force-device-scale-factor=1',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding'
                    ]
                )
                
                if mode == "mobile":
                    iphone = p.devices['iPhone 14 Pro']
                    context = await browser.new_context(
                        **iphone,
                        proxy=None
                    )
                else:
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                    )
                
                page = await context.new_page()
                
                await page.goto(url, wait_until='networkidle')

                # 确保页面稳定
                await page.wait_for_load_state('networkidle')

                try:
                    # 把一些登录窗口和打开APP的CSS元素隐藏了
                    await page.add_style_tag(content="""
                        .openapp-content, .m-fixed-openapp {
                            display: none !important;
                        }
                        .login-panel-popover, .login-tip {
                            display: none !important;
                        }
                    """)
                except Exception as e:
                    logger.warn("BilibiliScreenshot", f"样式注入失败: {e}")
                
                await asyncio.sleep(3)   
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                
                # 目标类区域截图
                target_selectors = ['.dyn-card', '.opus-modules', '.bili-dyn-item']
                screenshot_taken = False
                
                for selector in target_selectors:
                    if await page.locator(selector).is_visible():
                        try:
                            element = page.locator(selector)
                            await element.screenshot(
                                path=output_filename,
                            )
                            screenshot_taken = True
                            logger.info("BilibiliScreenshot", f"动态 {dynamic_id} 截图成功: {output_filename}")
                            break
                        except Exception as e:
                            logger.warn("BilibiliScreenshot", f"截图动态 {dynamic_id} 时出错: {e}")
                            continue
                
                # 保底一下，如果所有选择器都失败，截取整个页面
                if not screenshot_taken:
                    await page.screenshot(
                        path=output_filename, 
                        full_page=True
                    )
                    logger.info("BilibiliScreenshot", f"动态 {dynamic_id} 全页面截图成功: {output_filename}")
                
                await browser.close()
                return output_filename
                
        except Exception as e:
            logger.warn("BilibiliScreenshot", f"截图动态 {dynamic_id} 时出错: {e}")
            return ""
    
    def cleanup_old_screenshots(self, max_files: int = 20):
        """清理旧的截图文件，使用 FIFO 队列，只保留 max_files 个文件，默认为 20 个"""
        try:
            files = os.listdir(self.cache_dir)
            if len(files) > max_files:
                # 按修改时间排序，删除最旧的文件
                files_with_time = []
                for file in files:
                    file_path = os.path.join(self.cache_dir, file)
                    if os.path.isfile(file_path):
                        files_with_time.append((file_path, os.path.getmtime(file_path)))
                
                files_with_time.sort(key=lambda x: x[1])
                
                for file_path, _ in files_with_time[:-max_files]:
                    os.remove(file_path)
                    logger.info("BilibiliScreenshot", f"清理旧截图: {file_path}")
                    
        except Exception as e:
            logger.warn("BilibiliScreenshot", f"清理旧截图时出错: {e}")
